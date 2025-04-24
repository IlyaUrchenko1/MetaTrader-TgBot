from utils.logger import logger
import mt5_functions.mt5_api as mt5_api
import utils.constants as const
import math
import MetaTrader5 as mt5

# Core trading logic functions will go here
# e.g., calculate_lot, check_drawdown, manage_orders, etc.

# --- Helper Functions ---

def calculate_adjusted_distance(symbol_info, distance_pips):
    point = symbol_info.point
    stops_level = symbol_info.trade_stops_level
    # Convert pips to points (assuming 1 pip = 10 points for 5-digit, 1 point for 3-digit)
    # More robust check might be needed for exotic symbols
    pip_multiplier = 10 if symbol_info.digits == 5 or symbol_info.digits == 3 else 1
    distance_points = distance_pips * pip_multiplier

    adjusted_distance = max(distance_points, stops_level)
    if adjusted_distance > distance_points:
        logger.warning(f"Order distance ({distance_pips} pips / {distance_points} points) increased to broker's stops_level ({stops_level} points)")
    return adjusted_distance

def calculate_initial_lot(symbol_info, account_info):
    if const.INITIAL_LOT > 0:
        lot = const.INITIAL_LOT
        # logger.info(f"Using fixed initial lot: {lot}") # Keep log concise
    else:
        balance = account_info.balance
        percentage = const.BALANCE_PERCENT_FOR_LOT / 100.0
        target_amount = balance * percentage
        
        # Basic calculation: Lot = Target Amount / Margin for 1 Lot
        tick = mt5_api.get_symbol_tick(symbol_info.name)
        if not tick:
             logger.error("Cannot calculate lot based on balance: failed to get tick.")
             return 0.01 # Fallback to a small default lot
        
        margin_required_one_lot = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, symbol_info.name, 1.0, tick.ask)
        if not margin_required_one_lot or margin_required_one_lot <= 0:
            logger.warning(f"Could not calculate margin for {symbol_info.name}. Using fallback balance percentage calc.")
            # Simplified fallback - might be inaccurate
            lot = round((balance * percentage) / 1000, 2) 
        else:
            lot = round(target_amount / margin_required_one_lot, 2)

        # logger.info(f"Calculated initial lot based on {const.BALANCE_PERCENT_FOR_LOT}% of balance ({balance}): {lot}") # Keep log concise

    # Ensure lot meets symbol's volume constraints
    lot = max(lot, symbol_info.volume_min)
    lot = min(lot, symbol_info.volume_max)
    if symbol_info.volume_step > 0:
        lot = math.floor(lot / symbol_info.volume_step) * symbol_info.volume_step
    
    lot = round(lot, 2) # Final rounding

    if lot <= 0:
        logger.error(f"Calculated lot is zero or negative ({lot}). Falling back to minimum volume: {symbol_info.volume_min}")
        lot = symbol_info.volume_min

    # logger.info(f"Final adjusted initial lot: {lot}") # Log moved to initialize_strategy
    return lot

# --- Core Logic Functions ---

def initialize_strategy(state):
    logger.info("Initializing strategy...")
    symbol = const.SYMBOL
    magic = const.MAGIC_NUMBER

    # Check if already initialized (orders or positions exist)
    existing_orders = mt5_api.get_orders(symbol=symbol, magic=magic)
    existing_positions = mt5_api.get_positions(symbol=symbol, magic=magic)

    if existing_orders or existing_positions:
        logger.info(f"Strategy already has active orders ({len(existing_orders)}) or positions ({len(existing_positions)}). Initialization skipped.")
        # TODO: Load state relevant to existing grid (next lots, levels etc.)
        return False # Indicate no changes made

    logger.info("No existing orders or positions found for this magic number. Placing initial grid.")

    # Get necessary info
    symbol_info = mt5_api.get_symbol_info(symbol)
    account_info = mt5_api.get_account_info()
    tick = mt5_api.get_symbol_tick(symbol)

    if not symbol_info or not account_info or not tick:
        logger.error("Failed to get required info (symbol, account, tick) for initialization.")
        return False

    # Calculate parameters
    initial_lot = calculate_initial_lot(symbol_info, account_info)
    if initial_lot <= 0:
        logger.error("Initial lot calculation resulted in zero or negative value. Cannot place orders.")
        return False
        
    distance_points = calculate_adjusted_distance(symbol_info, const.ORDER_DISTANCE_PIPS)
    point = symbol_info.point
    digits = symbol_info.digits

    # Calculate prices
    buy_stop_price = round(tick.ask + distance_points * point, digits)
    sell_stop_price = round(tick.bid - distance_points * point, digits)
    
    # Normalize prices (using mt5 internal might be safer) --> Use Python's round instead
    # buy_stop_price = mt5.normalize_double(buy_stop_price, digits)
    # sell_stop_price = mt5.normalize_double(sell_stop_price, digits)
    # The round() function above already handles the normalization to the correct number of digits.

    logger.info(f"Calculated initial parameters: Lot={initial_lot}, Distance={distance_points} points, BuyStopPrice={buy_stop_price}, SellStopPrice={sell_stop_price}")

    # Prepare requests
    buy_request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": initial_lot,
        "type": mt5.ORDER_TYPE_BUY_STOP,
        "price": buy_stop_price,
        "magic": magic,
        "comment": "Grid Initial BuyStop",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": symbol_info.filling_mode # Use broker's preferred filling mode
    }

    sell_request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": initial_lot,
        "type": mt5.ORDER_TYPE_SELL_STOP,
        "price": sell_stop_price,
        "magic": magic,
        "comment": "Grid Initial SellStop",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": symbol_info.filling_mode
    }

    # Send orders
    buy_result = mt5_api.send_order(buy_request)
    sell_result = mt5_api.send_order(sell_request)
    
    orders_placed_count = 0
    buy_success = False
    sell_success = False

    # Check BuyStop result
    if buy_result and buy_result.order > 0 and buy_result.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
        logger.info(f"Initial BuyStop order accepted/placed successfully. Ticket: {buy_result.order}")
        orders_placed_count += 1
        buy_success = True
    else:
        logger.error(f"Failed to place initial BuyStop order. Result: {buy_result}")

    # Check SellStop result
    if sell_result and sell_result.order > 0 and sell_result.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
        logger.info(f"Initial SellStop order accepted/placed successfully. Ticket: {sell_result.order}")
        orders_placed_count += 1
        sell_success = True
    else:
        logger.error(f"Failed to place initial SellStop order. Result: {sell_result}")

    if orders_placed_count > 0:
        # Only update state if at least one order was placed successfully
        state['initialized'] = True
        if buy_success:
             state['initial_buy_stop_level'] = buy_stop_price
             state['last_placed_buy_lot'] = initial_lot
             state['next_buy_lot'] = round(initial_lot * const.LOT_MULTIPLIER, 2)
        if sell_success:
            state['initial_sell_stop_level'] = sell_stop_price
            state['last_placed_sell_lot'] = initial_lot
            state['next_sell_lot'] = round(initial_lot * const.LOT_MULTIPLIER, 2)
        
        # Store initial deposit only once
        if 'initial_deposit' not in state:
             state['initial_deposit'] = account_info.equity # Use equity at init time
             logger.info(f"Recorded initial deposit for drawdown calculation: {state['initial_deposit']}")
             
        logger.info(f"Strategy initialized partially or fully ({orders_placed_count} orders). State updated.")
        # Consider returning True even if only one order succeeded, 
        # the logic in check_and_manage_grid should handle inconsistencies.
        return True # Indicate state potentially changed
    else:
        logger.error("Failed to place any initial orders.")
        return False

def check_drawdown_and_close_all(state):
    initial_deposit = state.get('initial_deposit')
    if not initial_deposit:
        # Cannot check drawdown if initial deposit wasn't recorded
        return False

    account_info = mt5_api.get_account_info()
    if not account_info:
        logger.warning("Cannot check drawdown: failed to get account info.")
        return False

    current_equity = account_info.equity
    max_dd_percent = const.MAX_DRAWDOWN_PERCENT
    
    # Calculate drawdown
    drawdown = initial_deposit - current_equity
    drawdown_percent = (drawdown / initial_deposit) * 100 if initial_deposit > 0 else 0

    logger.debug(f"Drawdown Check: Initial={initial_deposit}, Current Equity={current_equity}, DD={drawdown:.2f} ({drawdown_percent:.2f}%), Max Allowed={max_dd_percent}%")

    if drawdown_percent >= max_dd_percent:
        logger.warning(f"MAX DRAWDOWN LIMIT REACHED: {drawdown_percent:.2f}% >= {max_dd_percent}%! Closing all positions and orders for magic {const.MAGIC_NUMBER}!")
        symbol = const.SYMBOL
        magic = const.MAGIC_NUMBER
        closed_count = 0
        cancelled_count = 0

        # 1. Close all open positions
        positions = mt5_api.get_positions(symbol=symbol, magic=magic)
        logger.info(f"Closing {len(positions)} positions...")
        for pos in positions:
            pos_type = pos.type
            pos_volume = pos.volume
            pos_symbol = pos.symbol
            pos_ticket = pos.ticket

            # Determine opposite action type
            close_action_type = mt5.ORDER_TYPE_SELL if pos_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
            
            # Get current price for closing
            tick = mt5_api.get_symbol_tick(pos_symbol)
            if not tick:
                logger.error(f"Could not get tick for {pos_symbol} to close position {pos_ticket}. Skipping.")
                continue
                
            price = tick.bid if close_action_type == mt5.ORDER_TYPE_SELL else tick.ask
            
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "position": pos_ticket,
                "symbol": pos_symbol,
                "volume": pos_volume,
                "type": close_action_type,
                "price": price,
                "deviation": const.DEFAULT_DEVIATION, # Allow some slippage for market close
                "magic": magic,
                "comment": "Drawdown Stop Out",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC, # IOC or FOK commonly used for closing
            }
            
            logger.info(f"Sending close request for position {pos_ticket} ({pos_symbol} {pos_type} {pos_volume})")
            result = mt5_api.send_order(close_request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                 logger.info(f"Successfully closed position {pos_ticket}. Result: {result}")
                 closed_count += 1
            else:
                 logger.error(f"Failed to close position {pos_ticket}. Result: {result}")
                 # Continue trying to close others

        # 2. Cancel all pending orders
        orders = mt5_api.get_orders(symbol=symbol, magic=magic)
        logger.info(f"Cancelling {len(orders)} pending orders...")
        for order in orders:
            if mt5_api.cancel_order(order.ticket):
                cancelled_count += 1
            # cancel_order already logs errors

        logger.warning(f"Drawdown Stop Out complete. Closed {closed_count}/{len(positions)} positions. Cancelled {cancelled_count}/{len(orders)} orders.")

        # 3. Reset state (keep initial_deposit for potential future reference?)
        state['initialized'] = False
        state.pop('initial_buy_stop_level', None)
        state.pop('initial_sell_stop_level', None)
        state.pop('next_buy_lot', None)
        state.pop('next_sell_lot', None)
        state.pop('last_placed_buy_lot', None)
        state.pop('last_placed_sell_lot', None)
        # state.pop('initial_deposit', None) # Optional: Decide whether to keep or remove
        logger.info("Strategy state has been reset due to drawdown stop out.")
        
        return True # Indicate that stop out occurred
    else:
        # Drawdown is within limits
        return False

def check_and_manage_grid(state):
    logger.debug("Checking and managing grid...")
    symbol = const.SYMBOL
    magic = const.MAGIC_NUMBER
    state_changed = False

    if not state.get('initialized', False):
        logger.debug("Strategy not initialized, skipping grid management.")
        return False

    # Get current market state
    orders = mt5_api.get_orders(symbol=symbol, magic=magic)
    positions = mt5_api.get_positions(symbol=symbol, magic=magic)
    symbol_info = mt5_api.get_symbol_info(symbol)
    if not symbol_info:
        logger.error("Cannot manage grid: failed to get symbol info.")
        return False

    # --- Identify triggered orders --- 
    # An order is considered triggered if it no longer exists in the orders list,
    # but a position with the corresponding direction and volume potentially exists.
    # We need the state to know what orders *should* exist.

    # Get expected order tickets from state (if stored)
    # For simplicity now, let's find orders by type and price level
    expected_buy_stop_level = state.get('initial_buy_stop_level')
    expected_sell_stop_level = state.get('initial_sell_stop_level')

    active_buy_stop = None
    active_sell_stop = None
    for o in orders:
        if o.type == mt5.ORDER_TYPE_BUY_STOP and o.price_open == expected_buy_stop_level:
            active_buy_stop = o
        elif o.type == mt5.ORDER_TYPE_SELL_STOP and o.price_open == expected_sell_stop_level:
            active_sell_stop = o
            
    # --- Check Buy Trigger --- 
    # If we expected a buy stop, but it's gone, assume it triggered (or was cancelled externally)
    # A more robust check involves matching position entry price/time or order fill history
    buy_triggered = False
    if expected_buy_stop_level and not active_buy_stop:
        # Check if a corresponding BUY position exists (simplistic check)
        # We need to know the *last placed* buy lot to potentially match volume
        last_buy_lot = state.get('last_placed_buy_lot')
        if any(p.type == mt5.POSITION_TYPE_BUY and p.volume == last_buy_lot for p in positions):
             logger.info(f"Detected potential BuyStop trigger at level {expected_buy_stop_level}.")
             buy_triggered = True
             # Action implemented below
             state_changed = True

    # --- Check Sell Trigger --- 
    # Similar logic for sell side
    sell_triggered = False
    if expected_sell_stop_level and not active_sell_stop:
        last_sell_lot = state.get('last_placed_sell_lot')
        # Ensure last_sell_lot is not None before comparison
        if last_sell_lot is not None and any(p.type == mt5.POSITION_TYPE_SELL and p.volume == last_sell_lot for p in positions):
             logger.info(f"Detected potential SellStop trigger at level {expected_sell_stop_level}.")
             sell_triggered = True
             # Action implemented below
             state_changed = True
             
    # --- Implement Actions based on triggers --- 
    if buy_triggered:
        logger.info("Handling Buy trigger...")
        # 1. Cancel existing SellStop (if any)
        if active_sell_stop:
            logger.info(f"Attempting to cancel SellStop order {active_sell_stop.ticket}")
            cancel_success = mt5_api.cancel_order(active_sell_stop.ticket)
            if not cancel_success:
                logger.warning(f"Failed to cancel SellStop {active_sell_stop.ticket}, continuing but state might be inconsistent.")
            else:
                 logger.info(f"Cancelled SellStop order {active_sell_stop.ticket}")
        else:
             logger.info("Buy triggered, and no active SellStop order found (expected if grid just started or after previous trigger).")
        
        # 2. Place new SellStop
        new_sell_lot = state.get('next_sell_lot')
        sell_level = state.get('initial_sell_stop_level') 
        last_buy_lot = state.get('last_placed_buy_lot') # Lot of the position that just triggered

        if new_sell_lot and sell_level and last_buy_lot:
             # Ensure lot meets symbol's volume constraints
             new_sell_lot = max(new_sell_lot, symbol_info.volume_min)
             new_sell_lot = min(new_sell_lot, symbol_info.volume_max)
             if symbol_info.volume_step > 0:
                new_sell_lot = math.floor(new_sell_lot / symbol_info.volume_step) * symbol_info.volume_step
             new_sell_lot = round(new_sell_lot, 2)

             if new_sell_lot > 0:
                logger.info(f"Placing new SellStop at {sell_level} with lot {new_sell_lot}")
                sell_request = {
                    "action": mt5.TRADE_ACTION_PENDING,
                    "symbol": symbol,
                    "volume": new_sell_lot,
                    "type": mt5.ORDER_TYPE_SELL_STOP,
                    "price": sell_level,
                    "magic": magic,
                    "comment": "Grid Sell",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": symbol_info.filling_mode
                }
                sell_result = mt5_api.send_order(sell_request)
                if sell_result and sell_result.order > 0 and sell_result.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
                    logger.info(f"New SellStop order accepted/placed successfully. Ticket: {sell_result.order}")
                    # Update state AFTER successful placement
                    state['last_placed_sell_lot'] = new_sell_lot
                    state['next_buy_lot'] = round(last_buy_lot * const.LOT_MULTIPLIER, 2) # Calculate next lot based on the one that TRIGGERED
                    # Mark the buy trigger as handled by removing its level from state
                    state.pop('initial_buy_stop_level', None)
                    logger.info(f"State updated: last_placed_sell_lot={state.get('last_placed_sell_lot')}, next_buy_lot={state.get('next_buy_lot')}, initial_buy_stop_level removed.")
                else:
                    logger.error(f"Failed to place new SellStop order. Result: {sell_result}. State not updated for this action.")
                    state_changed = False # Revert state change if this crucial step failed
             else:
                 logger.error(f"Calculated new sell lot is zero or negative ({new_sell_lot}). Cannot place order.")
                 state_changed = False
        else:
            logger.error("Cannot place new SellStop: Missing required state variables (next_sell_lot, initial_sell_stop_level, last_placed_buy_lot).")
            state_changed = False

    if sell_triggered:
        logger.info("Handling Sell trigger...")
        # 1. Cancel existing BuyStop (if any)
        if active_buy_stop:
            logger.info(f"Attempting to cancel BuyStop order {active_buy_stop.ticket}")
            cancel_success = mt5_api.cancel_order(active_buy_stop.ticket)
            if not cancel_success:
                logger.warning(f"Failed to cancel BuyStop {active_buy_stop.ticket}, continuing but state might be inconsistent.")
            else:
                logger.info(f"Cancelled BuyStop order {active_buy_stop.ticket}")
        else:
             logger.info("Sell triggered, and no active BuyStop order found (expected if grid just started or after previous trigger).")
             
        # 2. Place new BuyStop
        new_buy_lot = state.get('next_buy_lot')
        buy_level = state.get('initial_buy_stop_level')
        last_sell_lot = state.get('last_placed_sell_lot') # Lot of the position that just triggered

        if new_buy_lot and buy_level and last_sell_lot:
             # Ensure lot meets symbol's volume constraints
             new_buy_lot = max(new_buy_lot, symbol_info.volume_min)
             new_buy_lot = min(new_buy_lot, symbol_info.volume_max)
             if symbol_info.volume_step > 0:
                 new_buy_lot = math.floor(new_buy_lot / symbol_info.volume_step) * symbol_info.volume_step
             new_buy_lot = round(new_buy_lot, 2)

             if new_buy_lot > 0:
                logger.info(f"Placing new BuyStop at {buy_level} with lot {new_buy_lot}")
                buy_request = {
                    "action": mt5.TRADE_ACTION_PENDING,
                    "symbol": symbol,
                    "volume": new_buy_lot,
                    "type": mt5.ORDER_TYPE_BUY_STOP,
                    "price": buy_level,
                    "magic": magic,
                    "comment": "Grid Buy",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": symbol_info.filling_mode
                }
                buy_result = mt5_api.send_order(buy_request)
                if buy_result and buy_result.order > 0 and buy_result.retcode in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
                    logger.info(f"New BuyStop order accepted/placed successfully. Ticket: {buy_result.order}")
                    # Update state AFTER successful placement
                    state['last_placed_buy_lot'] = new_buy_lot
                    state['next_sell_lot'] = round(last_sell_lot * const.LOT_MULTIPLIER, 2) # Calculate next lot based on the one that TRIGGERED
                    # Mark the sell trigger as handled by removing its level from state
                    state.pop('initial_sell_stop_level', None)
                    logger.info(f"State updated: last_placed_buy_lot={state.get('last_placed_buy_lot')}, next_sell_lot={state.get('next_sell_lot')}, initial_sell_stop_level removed.")
                else:
                    logger.error(f"Failed to place new BuyStop order. Result: {buy_result}. State not updated for this action.")
                    state_changed = False # Revert state change if this crucial step failed
             else:
                 logger.error(f"Calculated new buy lot is zero or negative ({new_buy_lot}). Cannot place order.")
                 state_changed = False
        else:
             logger.error("Cannot place new BuyStop: Missing required state variables (next_buy_lot, initial_buy_stop_level, last_placed_sell_lot).")
             state_changed = False

    # Ensure state_changed reflects if *any* action successfully modified the state
    # The logic above sets state_changed = False if placing the new order fails.
    if state_changed:
        logger.info("Grid managed. State updated.") # Changed log message slightly

    return state_changed

if __name__ == '__main__':
    logger.info("trading_service.py executed directly (for testing/example)")
    # Example usage or tests can be placed here
    pass
