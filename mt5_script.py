import time
import MetaTrader5 as mt5
import sys

from utils.logger import logger
import utils.constants as const
from utils.state_manager import load_state, save_state
import mt5_functions.mt5_api as mt5_api
import mt5_functions.trading_service as trading_service

def main():
    logger.info("Starting MT5 Trading Bot...")

    if not mt5_api.connect_mt5():
        logger.error("Failed to initialize MetaTrader 5. Exiting.")
        sys.exit(1)

    state = load_state()
    logger.info(f"Loaded initial state: {state}")

    # Initialize strategy (place initial orders if none exist)
    try:
        state_changed = trading_service.initialize_strategy(state)
        if state_changed:
            save_state(state) # Save state immediately after initialization
            logger.info("Initial state saved after successful initialization.")
    except Exception as e:
        logger.error(f"Error during initial strategy initialization: {e}", exc_info=True)
        # Decide if we should exit or continue without initialization
        # For now, let's continue, maybe connection is temporary issue

    is_running = True
    try:
        while is_running:
            # Basic connection check (can be improved)
            if not mt5.terminal_info():
                logger.error("MetaTrader 5 terminal connection lost. Attempting to reconnect...")
                if not mt5_api.connect_mt5():
                    logger.error("Reconnect failed. Exiting loop.")
                    is_running = False
                    continue
                else:
                    logger.info("Successfully reconnected to MetaTrader 5.")
            
            # --- Monitor Orders and Positions --- 
            current_orders = mt5_api.get_orders(symbol=const.SYMBOL, magic=const.MAGIC_NUMBER)
            current_positions = mt5_api.get_positions(symbol=const.SYMBOL, magic=const.MAGIC_NUMBER)
            logger.info(f"Monitoring: Found {len(current_orders)} active orders and {len(current_positions)} positions for magic {const.MAGIC_NUMBER}.")
            # Detailed logging (optional)
            # for order in current_orders:
            #    logger.debug(f"  Order: {order.ticket}, Type: {order.type}, Price: {order.price_open}, Volume: {order.volume_initial}")
            # for position in current_positions:
            #    logger.debug(f"  Position: {position.ticket}, Type: {position.type}, Price: {position.price_open}, Volume: {position.volume}, Profit: {position.profit}")

            # TODO: Check drawdown
            # drawdown_exceeded = trading_service.check_drawdown_and_close_all(state)
            # if drawdown_exceeded:
            #     is_running = False # Stop the loop if max drawdown is hit
            #     save_state(state) # Save state before exiting
            #     continue

            # Manage grid (check triggers, place/delete orders)
            try:
                grid_state_changed = trading_service.check_and_manage_grid(state)
                if grid_state_changed:
                    save_state(state)
            except Exception as e:
                logger.error(f"Error during grid management: {e}", exc_info=True)
                # Decide if we need to stop or just log and continue
                # For now, log and continue

            logger.info("Main loop iteration finished. Waiting...")
            time.sleep(const.LOOP_DELAY_SECONDS)

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received. Shutting down...")
    except Exception as e: # Catch unexpected errors in the main loop
        logger.error(f"Unhandled exception in main loop: {e}", exc_info=True)
    finally:
        logger.info("Saving final state...")
        save_state(state) # Save state on exit
        mt5_api.disconnect_mt5()
        logger.info("MT5 Trading Bot stopped.")

if __name__ == "__main__":
    main()
