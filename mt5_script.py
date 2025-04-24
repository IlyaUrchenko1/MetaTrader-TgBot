import time
import sys
import MetaTrader5 as mt5

from utils.logger import logger
import utils.constants as const
from utils.state_manager import load_state, save_state
import mt5_functions.mt5_api as mt5_api
import mt5_functions.trading_service as trading_service

def run_bot():
    """Main function to run the trading bot logic."""
    logger.info("Starting MT5 Trading Bot...")

    # --- Initial Connection ---
    if not mt5_api.connect_mt5():
        logger.error("Fatal: Failed to initialize MetaTrader 5 connection on startup. Exiting.")
        sys.exit(1)

    # --- Load Initial State ---
    state = load_state()
    logger.info(f"Loaded initial state: {state}")

    is_running = True
    while is_running:
        try:
            # --- 1. Check Connection --- 
            if not mt5.terminal_info(): # Quick check if terminal is available
                logger.error("MetaTrader 5 terminal connection lost. Attempting to reconnect...")
                time.sleep(const.LOOP_DELAY_SECONDS) # Wait before reconnect attempt
                if not mt5_api.connect_mt5():
                    logger.error("Fatal: Reconnect failed. Stopping the bot.")
                    is_running = False
                    continue # Skip to the end of the loop
                else:
                    logger.info("Successfully reconnected to MetaTrader 5.")
                    # Re-fetch state potentially missed during disconnection? For now, continue.
            
            # --- 2. Check Drawdown --- 
            # Perform drawdown check first, as it can reset the state
            drawdown_hit = False
            try:
                drawdown_hit = trading_service.check_drawdown_and_close_all(state)
                if drawdown_hit:
                    logger.warning("Drawdown limit hit. Strategy halted and state reset.")
                    save_state(state) # Save the reset state
                    is_running = False # Stop the main loop after reset
                    continue # Skip the rest of this iteration
            except Exception as e:
                logger.error(f"Error during drawdown check: {e}", exc_info=True)
                # Consider if bot should stop on drawdown check error. For now, continue.

            # --- 3. Initialize Strategy (if needed) ---
            # Check if strategy needs initialization (only if not already initialized)
            if not state.get('initialized', False):
                logger.info("Strategy requires initialization.")
                try:
                    initialized_now = trading_service.initialize_strategy(state)
                    if initialized_now:
                        logger.info("Strategy initialized successfully in this cycle.")
                        save_state(state) # Save state after successful init
                    else:
                        # Might fail due to market conditions or temporary errors
                        logger.warning("Initialization attempt failed or was skipped (e.g., existing orders). Will retry next cycle.")
                except Exception as e:
                    logger.error(f"Error during strategy initialization: {e}", exc_info=True)
                    # Continue, will retry initialization in the next cycle
            
            # --- 4. Manage Grid (if initialized) ---
            # Only manage grid if the strategy is marked as initialized
            if state.get('initialized', False):
                try:
                    grid_state_changed = trading_service.check_and_manage_grid(state)
                    if grid_state_changed:
                        logger.info("Grid state was modified, saving state.")
                        save_state(state)
                    else:
                        logger.debug("Grid check complete, no changes required.")
                except Exception as e:
                    logger.error(f"Error during grid management: {e}", exc_info=True)
                    # Continue, assuming temporary error or issue with a single cycle
            else:
                 logger.debug("Skipping grid management as strategy is not initialized.")

            # --- 5. Monitoring (Optional Logging) ---
            # Placed after management actions to reflect current state
            current_orders = mt5_api.get_orders(symbol=const.SYMBOL, magic=const.MAGIC_NUMBER)
            current_positions = mt5_api.get_positions(symbol=const.SYMBOL, magic=const.MAGIC_NUMBER)
            logger.info(f"Monitoring: {len(current_orders)} orders, {len(current_positions)} positions (Magic: {const.MAGIC_NUMBER})")

            # --- 6. Wait for next cycle --- 
            logger.debug(f"Main loop iteration finished. Waiting for {const.LOOP_DELAY_SECONDS} seconds...")
            time.sleep(const.LOOP_DELAY_SECONDS)

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received. Initiating shutdown...")
            is_running = False # Signal loop to stop
        except Exception as e: # Catch unexpected errors in the main loop itself
            logger.error(f"Unhandled exception in main loop: {e}", exc_info=True)
            # Consider adding a delay or specific recovery logic here if needed
            time.sleep(const.LOOP_DELAY_SECONDS) # Basic delay to prevent rapid error loops

    # --- Shutdown Sequence ---
    logger.info("Bot loop finished. Finalizing...")
    try:
        # Save the very final state, whatever it may be
        logger.info("Saving final state...")
        save_state(state) 
    except Exception as e:
         logger.error(f"Error saving final state: {e}", exc_info=True)
         
    mt5_api.disconnect_mt5()
    logger.info("MT5 Trading Bot stopped gracefully.")

if __name__ == "__main__":
    run_bot() # Call the main bot function
