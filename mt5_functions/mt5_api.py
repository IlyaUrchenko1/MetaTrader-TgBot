import MetaTrader5 as mt5
from utils.logger import logger
import time

def connect_mt5():
    if not mt5.initialize():
        logger.error(f"initialize() failed, error code = {mt5.last_error()}")
        return False
    logger.info(f"MetaTrader5 initialized successfully. Version: {mt5.version()}")
    # Additional checks like login status could be added here if needed
    return True

def disconnect_mt5():
    mt5.shutdown()
    logger.info("MetaTrader5 connection shut down.")

def get_account_info():
    account_info = mt5.account_info()
    if account_info is None:
        logger.error(f"Failed to get account info, error code = {mt5.last_error()}")
        return None
    return account_info

def get_symbol_info(symbol):
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        logger.error(f"Failed to get symbol info for {symbol}, error code = {mt5.last_error()}")
        return None
    # Ensure the symbol is available in MarketWatch
    if not symbol_info.visible:
        logger.warning(f"Symbol {symbol} is not visible in MarketWatch. Attempting to select.")
        if not mt5.symbol_select(symbol, True):
            logger.error(f"Failed to select symbol {symbol} in MarketWatch, error code = {mt5.last_error()}")
            return None
        # Retry getting info after selecting
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.error(f"Failed to get symbol info for {symbol} even after selecting, error code = {mt5.last_error()}")
            return None
    return symbol_info

def get_symbol_tick(symbol):
    symbol_tick = mt5.symbol_info_tick(symbol)
    if symbol_tick is None:
        logger.error(f"Failed to get symbol tick for {symbol}, error code = {mt5.last_error()}")
        return None
    return symbol_tick

# --- Functions for Trading Operations ---

def get_positions(symbol=None, magic=None):
    try:
        if symbol:
            if magic:
                positions = mt5.positions_get(symbol=symbol, magic=magic)
            else:
                positions = mt5.positions_get(symbol=symbol)
        elif magic:
            positions = mt5.positions_get(magic=magic)
        else:
            positions = mt5.positions_get()

        if positions is None:
            logger.error(f"Failed to get positions, error code = {mt5.last_error()}")
            return [] # Return empty list on error
        return list(positions)
    except Exception as e:
        logger.error(f"Exception in get_positions: {e}")
        return []

def get_orders(symbol=None, magic=None):
    try:
        if symbol:
            if magic:
                 # Note: mt5.orders_get doesn't have magic filter, filter manually
                orders = mt5.orders_get(symbol=symbol)
            else:
                orders = mt5.orders_get(symbol=symbol)
        else:
            orders = mt5.orders_get()

        if orders is None:
            logger.error(f"Failed to get orders, error code = {mt5.last_error()}")
            return []

        orders_list = list(orders)
        if magic:
            # Filter by magic number if specified
            orders_list = [o for o in orders_list if o.magic == magic]

        return orders_list
    except Exception as e:
        logger.error(f"Exception in get_orders: {e}")
        return []

def cancel_order(ticket):
    logger.info(f"Attempting to cancel order ticket: {ticket}")
    request = {
        "action": mt5.TRADE_ACTION_REMOVE, # Action type for removing pending orders
        "order": ticket,
        "comment": "Grid Strategy: Canceling order"
    }
    result = send_order(request) # Use our send_order wrapper
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info(f"Successfully cancelled order ticket: {ticket}, result: {result}")
        return True
    else:
        logger.error(f"Failed to cancel order ticket: {ticket}, result: {result}")
        return False

def send_order(request):
    # Simple wrapper for now, retry logic can be added here or in trading_service
    logger.debug(f"Sending order request: {request}")
    try:
        result = mt5.order_send(request)
        if result is None:
            logger.error(f"order_send failed, error code = {mt5.last_error()}")
            return None
        logger.info(f"Order send result: {result}")
        # Basic check for common errors (could be expanded)
        if result.retcode not in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
             logger.warning(f"Order send request executed with code: {result.retcode}, comment: {result.comment}")
        return result
    except Exception as e:
        logger.error(f"Exception during order_send: {e}")
        return None

# Functions for interacting with the MetaTrader 5 API will go here
# e.g., get_symbol_info, get_account_info, place_order, etc.

if __name__ == '__main__':
    logger.info("mt5_api.py executed directly (for testing/example)")
    if connect_mt5():
        # Test account info
        acc_info = get_account_info()
        if acc_info:
            logger.info(f"Account Info: Login={acc_info.login}, Balance={acc_info.balance}, Equity={acc_info.equity}")

        # Test symbol info (use a common symbol like EURUSD)
        test_symbol = "EURUSD"
        sym_info = get_symbol_info(test_symbol)
        if sym_info:
            logger.info(f"Symbol Info ({test_symbol}): Point={sym_info.point}, Digits={sym_info.digits}, StopLevel={sym_info.trade_stops_level}")

        # Test tick info
        tick_info = get_symbol_tick(test_symbol)
        if tick_info:
            logger.info(f"Tick Info ({test_symbol}): Bid={tick_info.bid}, Ask={tick_info.ask}, Time={tick_info.time}")

        # Test get_positions
        positions = get_positions(magic=12345) # Example magic number
        logger.info(f"Found {len(positions)} positions with magic 12345: {positions}")

        # Test get_orders
        orders = get_orders(magic=12345) # Example magic number
        logger.info(f"Found {len(orders)} orders with magic 12345: {orders}")

        # Test order placement (Example: place a small pending order if none exist)
        if not orders and not positions:
            logger.info("Placing a test Buy Stop order...")
            symbol_info = get_symbol_info(test_symbol)
            tick = get_symbol_tick(test_symbol)
            if symbol_info and tick:
                price = round(tick.ask + 50 * symbol_info.point, symbol_info.digits)
                test_request = {
                    "action": mt5.TRADE_ACTION_PENDING,
                    "symbol": test_symbol,
                    "volume": 0.01,
                    "type": mt5.ORDER_TYPE_BUY_STOP,
                    "price": price,
                    "magic": 12345,
                    "comment": "API Test Order",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": mt5.ORDER_FILLING_IOC, # Or FOK depending on broker
                }
                result = send_order(test_request)
                if result and result.order:
                    test_order_ticket = result.order
                    logger.info(f"Placed test order with ticket: {test_order_ticket}")
                    # Test cancel order
                    time.sleep(2) # Give time for order to appear
                    if cancel_order(test_order_ticket):
                        logger.info("Successfully cancelled test order.")
                    else:
                        logger.error("Failed to cancel test order.")
            else:
                logger.warning("Could not get symbol/tick info to place test order.")
        else:
            logger.info("Skipping test order placement as existing orders/positions found.")

        disconnect_mt5()
    else:
        logger.error("Failed to connect to MetaTrader5 terminal.")
