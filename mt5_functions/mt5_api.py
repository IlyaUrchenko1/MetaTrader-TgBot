import traceback
import MetaTrader5 as mt5
import time
from typing import Dict, Any, List, Optional, Tuple, Union
import pandas as pd

MT5_TERMINAL_PATH: Optional[str] = None

def initialize_mt5(path: Optional[str] = None) -> Dict[str, Any]:
    global MT5_TERMINAL_PATH
    if path:
        MT5_TERMINAL_PATH = path

    try:
        terminal_info = mt5.terminal_info()
        if terminal_info is not None and terminal_info.connected:
            return {"success": True, "data": terminal_info, "error": None}

        if not mt5.initialize(path=MT5_TERMINAL_PATH):
            error_code, error_message = mt5.last_error()
            err_str = f"MT5 Initialization failed. Error code: {error_code} - {error_message}"
            print(err_str)
            return {"success": False, "data": None, "error": err_str}

        terminal_info = mt5.terminal_info()
        if terminal_info is None or not terminal_info.connected:
            err_str = "MT5 initialized but failed to connect to the terminal."
            print(err_str)
            mt5.shutdown()
            return {"success": False, "data": None, "error": err_str}

        print(f"MT5 Initialized successfully. Terminal: {terminal_info.name}, Build: {terminal_info.build}")
        return {"success": True, "data": terminal_info, "error": None}
    except Exception as e:
        err_str = f"Exception during MT5 initialization: {e}\n{traceback.format_exc()}"
        print(err_str)
        try:
            mt5.shutdown()
        except Exception as shutdown_e:
            print(f"Exception during MT5 shutdown after init error: {shutdown_e}")
        return {"success": False, "data": None, "error": err_str}

def shutdown_mt5() -> Dict[str, Any]:
    try:
        mt5.shutdown()
        print("MT5 Connection shut down.")
        return {"success": True, "error": None}
    except Exception as e:
        err_str = f"Exception during MT5 shutdown: {e}"
        print(err_str)
        return {"success": False, "error": err_str}

def _ensure_initialized() -> bool:
    term_info = mt5.terminal_info()
    if term_info is None or not term_info.connected:
        print("MT5 connection lost or not initialized. Attempting to reconnect...")
        init_result = initialize_mt5()
        return init_result["success"]
    return True

def get_terminal_info() -> Dict[str, Any]:
    if not _ensure_initialized():
        return {"success": False, "data": None, "error": "MT5 connection failed"}
    try:
        info = mt5.terminal_info()
        if info:
            return {"success": True, "data": info._asdict(), "error": None}
        else:
            return {"success": False, "data": None, "error": "Failed to retrieve terminal info"}
    except Exception as e:
        err_str = f"Exception retrieving terminal info: {e}"
        print(err_str)
        return {"success": False, "data": None, "error": err_str}

def get_account_info() -> Dict[str, Any]:
    if not _ensure_initialized():
        return {"success": False, "data": None, "error": "MT5 connection failed"}
    try:
        info = mt5.account_info()
        if info:
            return {"success": True, "data": info._asdict(), "error": None}
        else:
            error_code, error_message = mt5.last_error()
            err_str = f"Failed to retrieve account info. Error {error_code}: {error_message}"
            print(err_str)
            return {"success": False, "data": None, "error": err_str}
    except Exception as e:
        err_str = f"Exception retrieving account info: {e}"
        print(err_str)
        return {"success": False, "data": None, "error": err_str}

def get_symbols(only_visible: bool = True) -> Dict[str, Any]:
    if not _ensure_initialized():
        return {"success": False, "data": None, "error": "MT5 connection failed"}
    try:
        if only_visible:
            symbols = mt5.symbols_get()
        else:
            print("Warning: get_symbols(only_visible=False) currently only returns visible symbols.")
            symbols = mt5.symbols_get()

        if symbols:
            return {"success": True, "data": [s._asdict() for s in symbols], "error": None}
        else:
            error_code, error_message = mt5.last_error()
            err_str = f"Failed to retrieve symbols. Error {error_code}: {error_message}"
            print(err_str)
            return {"success": False, "data": None, "error": err_str}
    except Exception as e:
        err_str = f"Exception retrieving symbols: {e}"
        print(err_str)
        return {"success": False, "data": None, "error": err_str}

def select_symbol(symbol: str, enable: bool = True) -> Dict[str, Any]:
    if not _ensure_initialized():
        return {"success": False, "error": "MT5 connection failed"}
    try:
        if mt5.symbol_select(symbol, enable):
            return {"success": True, "error": None}
        else:
            error_code, error_message = mt5.last_error()
            err_str = f"Failed to {'select' if enable else 'deselect'} symbol {symbol}. Error {error_code}: {error_message}"
            print(err_str)
            if enable and mt5.symbol_info(symbol):
                 print(f"Symbol {symbol} might already be selected.")
                 return {"success": True, "error": None}
            return {"success": False, "error": err_str}
    except Exception as e:
        err_str = f"Exception {'selecting' if enable else 'deselecting'} symbol {symbol}: {e}"
        print(err_str)
        return {"success": False, "error": err_str}

def get_symbol_info(symbol: str) -> Dict[str, Any]:
    if not _ensure_initialized():
        return {"success": False, "data": None, "error": "MT5 connection failed"}
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            print(f"Symbol {symbol} not found initially, attempting to select...")
            select_result = select_symbol(symbol, True)
            if not select_result["success"]:
                return {"success": False, "data": None, "error": f"Symbol {symbol} not found and failed to select."}
            info = mt5.symbol_info(symbol)
            if info is None:
                error_code, error_message = mt5.last_error()
                err_str = f"Failed to retrieve symbol info for {symbol} even after selection. Error {error_code}: {error_message}"
                print(err_str)
                return {"success": False, "data": None, "error": err_str}

        trade_mode = info.trade_mode
        allowed = trade_mode == mt5.SYMBOL_TRADE_MODE_FULL

        data = info._asdict()
        data["trade_allowed"] = allowed

        return {"success": True, "data": data, "error": None}

    except Exception as e:
        err_str = f"Exception retrieving symbol info for {symbol}: {e}"
        print(err_str)
        return {"success": False, "data": None, "error": err_str}

def get_symbol_tick(symbol: str) -> Dict[str, Any]:
    if not _ensure_initialized():
        return {"success": False, "data": None, "error": "MT5 connection failed"}
    try:
        info_res = get_symbol_info(symbol)
        if not info_res["success"]:
             return {"success": False, "data": None, "error": f"Cannot get tick, symbol {symbol} info unavailable: {info_res['error']}"}

        tick = mt5.symbol_info_tick(symbol)
        if tick and tick.time != 0:
            return {"success": True, "data": tick._asdict(), "error": None}
        else:
            rates_res = get_rates(symbol, mt5.TIMEFRAME_M1, 0, 1)
            if rates_res["success"] and rates_res["data"] is not None and len(rates_res["data"]) > 0:
                last_close = rates_res["data"][0]['close']
                print(f"Warning: Failed to get live tick for {symbol}. Using last M1 close price: {last_close}")
                return {
                    "success": True,
                    "data": {"ask": last_close, "bid": last_close, "last": last_close, "time": rates_res["data"][0]['time'], "volume": 0},
                    "error": "Live tick unavailable, used last close price"
                }
            else:
                error_code, error_message = mt5.last_error()
                err_str = f"Failed to retrieve tick for {symbol}. Error {error_code}: {error_message}. Fallback failed: {rates_res.get('error', 'Unknown rates error')}"
                print(err_str)
                return {"success": False, "data": None, "error": err_str}
    except Exception as e:
        err_str = f"Exception retrieving tick for {symbol}: {e}"
        print(err_str)
        return {"success": False, "data": None, "error": err_str}

def normalize_price(price: float, symbol: str) -> float:
    info_res = get_symbol_info(symbol)
    if info_res["success"] and info_res["data"]:
        digits = info_res["data"].get("digits")
        if digits is not None:
            return round(price, digits)
    print(f"Warning: Could not normalize price for {symbol}, using original value. Error: {info_res.get('error')}")
    return price

def get_rates(symbol: str, timeframe: int, start_pos: int, count: int) -> Dict[str, Any]:
    if not _ensure_initialized():
        return {"success": False, "data": None, "error": "MT5 connection failed"}
    try:
        info_res = get_symbol_info(symbol)
        if not info_res["success"]:
             return {"success": False, "data": None, "error": f"Cannot get rates, symbol {symbol} info unavailable: {info_res['error']}"}

        rates = mt5.copy_rates_from_pos(symbol, timeframe, start_pos, count)
        if rates is not None:
            rates_list = [
                {
                    "time": int(r[0]), "open": r[1], "high": r[2], "low": r[3],
                    "close": r[4], "tick_volume": int(r[5]), "spread": int(r[6]),
                    "real_volume": int(r[7])
                 } for r in rates
            ]
            return {"success": True, "data": rates_list, "error": None}
        else:
            error_code, error_message = mt5.last_error()
            err_str = f"Failed to retrieve rates for {symbol}. Error {error_code}: {error_message}"
            print(err_str)
            return {"success": False, "data": None, "error": err_str}
    except Exception as e:
        err_str = f"Exception retrieving rates for {symbol}: {e}"
        print(err_str)
        return {"success": False, "data": None, "error": err_str}

def _format_order(order) -> Dict[str, Any]:
    if not order:
        return {}
    return order._asdict()

def _format_position(position) -> Dict[str, Any]:
    if not position:
        return {}
    return position._asdict()

def get_orders(symbol: Optional[str] = None, ticket: Optional[int] = None, magic: Optional[int] = None) -> Dict[str, Any]:
    if not _ensure_initialized():
        return {"success": False, "data": None, "error": "MT5 connection failed"}
    try:
        if ticket:
            orders = mt5.orders_get(ticket=ticket)
        elif symbol:
            orders = mt5.orders_get(symbol=symbol)
        else:
            orders = mt5.orders_get()

        if orders is None:
            error_code, error_message = mt5.last_error()
            err_str = f"Failed to retrieve orders. Error {error_code}: {error_message}"
            return {"success": True, "data": [], "error": None}

        orders_list = [_format_order(o) for o in orders]

        if magic is not None:
            orders_list = [o for o in orders_list if o.get('magic') == magic]

        return {"success": True, "data": orders_list, "error": None}
    except Exception as e:
        err_str = f"Exception retrieving orders: {e}"
        print(err_str)
        return {"success": False, "data": None, "error": err_str}

def get_positions(symbol: Optional[str] = None, ticket: Optional[int] = None, magic: Optional[int] = None) -> Dict[str, Any]:
    if not _ensure_initialized():
        return {"success": False, "data": None, "error": "MT5 connection failed"}
    try:
        if ticket:
            positions = mt5.positions_get(ticket=ticket)
        elif symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()

        if positions is None:
            error_code, error_message = mt5.last_error()
            err_str = f"Failed to retrieve positions. Error {error_code}: {error_message}"
            return {"success": True, "data": [], "error": None}

        positions_list = [_format_position(p) for p in positions]

        if magic is not None:
            positions_list = [p for p in positions_list if p.get('magic') == magic]

        return {"success": True, "data": positions_list, "error": None}
    except Exception as e:
        err_str = f"Exception retrieving positions: {e}"
        print(err_str)
        return {"success": False, "data": None, "error": err_str}

def _determine_filling_type(symbol: str) -> Optional[int]:
    info_res = get_symbol_info(symbol)
    if not info_res["success"] or not info_res["data"]:
        print(f"Warning: Could not get symbol info for {symbol} to determine filling type. Error: {info_res.get('error')}")
        return mt5.ORDER_FILLING_IOC

    filling_mode = info_res["data"].get("filling_mode")
    if filling_mode is None:
        return mt5.ORDER_FILLING_IOC

    if filling_mode & mt5.ORDER_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK
    elif filling_mode & mt5.ORDER_FILLING_IOC:
        return mt5.ORDER_FILLING_IOC
    elif filling_mode & mt5.ORDER_FILLING_RETURN:
        return mt5.ORDER_FILLING_RETURN
    else:
        print(f"Warning: Unknown filling mode {filling_mode} for {symbol}. Defaulting to IOC.")
        return mt5.ORDER_FILLING_IOC

def send_order(request: Dict[str, Any]) -> Dict[str, Any]:
    if not _ensure_initialized():
        return {"success": False, "data": None, "error": "MT5 connection failed"}

    symbol = request.get("symbol")
    if not symbol:
         if request.get("action") == mt5.TRADE_ACTION_DEAL and request.get("position"):
             pos_res = get_positions(ticket=request["position"])
             if pos_res["success"] and pos_res["data"]:
                 symbol = pos_res["data"][0].get("symbol")

    if symbol and "type_filling" not in request:
        filling_type = _determine_filling_type(symbol)
        if filling_type is not None:
            request["type_filling"] = filling_type
        else:
            return {"success": False, "data": None, "error": f"Failed to determine filling type for symbol {symbol}"}
    elif "type_filling" not in request:
        request["type_filling"] = mt5.ORDER_FILLING_IOC
        print(f"Warning: Using default filling type IOC for request: {request.get('action')}")

    if "volume" in request and symbol:
        info_res = get_symbol_info(symbol)
        if info_res["success"] and info_res["data"]:
             volume_step = info_res["data"].get("volume_step", 0.01)
             request["volume"] = round(request["volume"] / volume_step) * volume_step

    if "type_time" not in request:
        request["type_time"] = mt5.ORDER_TIME_GTC

    try:
        print(f"Sending order request: {request}")
        result = mt5.order_send(request)
        time.sleep(0.1)

        if result is None:
            error_code, error_message = mt5.last_error()
            err_str = f"Order send failed (result is None). Request: {request}. Error {error_code}: {error_message}"
            print(err_str)
            return {"success": False, "data": None, "error": err_str}

        if result.retcode == mt5.TRADE_RETCODE_DONE or result.retcode == mt5.TRADE_RETCODE_PLACED:
            print(f"Order request successful. Result: {result}")
            return {"success": True, "data": result._asdict(), "error": None}
        else:
            err_str = f"Order send failed. Request: {request}. Retcode: {result.retcode}, Comment: {result.comment}"
            print(err_str)
            return {"success": False, "data": result._asdict(), "error": err_str}

    except Exception as e:
        err_str = f"Exception during order send. Request: {request}. Error: {e}\n{traceback.format_exc()}"
        print(err_str)
        return {"success": False, "data": None, "error": err_str}

def close_position(ticket: int, deviation: int = 10) -> Dict[str, Any]:
    if not _ensure_initialized():
        return {"success": False, "error": "MT5 connection failed"}

    pos_res = get_positions(ticket=ticket)
    if not pos_res["success"] or not pos_res["data"]:
        return {"success": False, "error": f"Position {ticket} not found or error retrieving: {pos_res.get('error', 'Unknown')}"}

    position = pos_res["data"][0]
    symbol = position["symbol"]
    volume = position["volume"]
    pos_type = position["type"]
    magic = position["magic"]
    comment = f"Closing position {ticket}"

    close_order_type = mt5.ORDER_TYPE_SELL if pos_type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY

    tick_res = get_symbol_tick(symbol)
    if not tick_res["success"] or not tick_res["data"]:
        return {"success": False, "error": f"Cannot get current price for {symbol} to close position {ticket}. Error: {tick_res.get('error')}"}

    price = tick_res["data"]["bid"] if close_order_type == mt5.ORDER_TYPE_SELL else tick_res["data"]["ask"]

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": ticket,
        "symbol": symbol,
        "volume": volume,
        "type": close_order_type,
        "price": price,
        "deviation": deviation,
        "magic": magic,
        "comment": comment,
    }

    return send_order(request)

def delete_order(ticket: int) -> Dict[str, Any]:
    if not _ensure_initialized():
        return {"success": False, "error": "MT5 connection failed"}

    order_res = get_orders(ticket=ticket)
    if not order_res["success"] or not order_res["data"]:
         print(f"Warning: Could not confirm order {ticket} exists before deletion attempt. Error: {order_res.get('error', 'Unknown')}")

    request = {
        "action": mt5.TRADE_ACTION_REMOVE,
        "order": ticket,
        "comment": f"Deleting order {ticket}",
    }

    return send_order(request)

def order_type_to_string(order_type: int) -> str:
    types = {
        mt5.ORDER_TYPE_BUY: "Buy",
        mt5.ORDER_TYPE_SELL: "Sell",
        mt5.ORDER_TYPE_BUY_LIMIT: "Buy Limit",
        mt5.ORDER_TYPE_SELL_LIMIT: "Sell Limit",
        mt5.ORDER_TYPE_BUY_STOP: "Buy Stop",
        mt5.ORDER_TYPE_SELL_STOP: "Sell Stop",
        mt5.ORDER_TYPE_BUY_STOP_LIMIT: "Buy Stop Limit",
        mt5.ORDER_TYPE_SELL_STOP_LIMIT: "Sell Stop Limit",
        mt5.ORDER_TYPE_CLOSE_BY: "Close By",
    }
    return types.get(order_type, f"Unknown ({order_type})")

def position_type_to_string(position_type: int) -> str:
    types = {
        mt5.POSITION_TYPE_BUY: "Buy",
        mt5.POSITION_TYPE_SELL: "Sell",
    }
    return types.get(position_type, f"Unknown ({position_type})")

if __name__ == '__main__':
    print("Running MT5 API Sanity Checks...")

    terminal_path = None

    init_res = initialize_mt5(path=terminal_path)
    if not init_res["success"]:
        print(f"Initialization failed: {init_res['error']}")
        exit()

    print("\n--- Terminal Info ---")
    term_info_res = get_terminal_info()
    if term_info_res["success"]:
        print(term_info_res["data"])
    else:
        print(f"Error: {term_info_res['error']}")

    print("\n--- Account Info ---")
    acc_info_res = get_account_info()
    if acc_info_res["success"]:
        print(acc_info_res["data"])
    else:
        print(f"Error: {acc_info_res['error']}")

    print("\n--- Symbols (Visible) ---")
    sym_res = get_symbols(only_visible=True)
    if sym_res["success"] and sym_res["data"]:
        print(f"Found {len(sym_res['data'])} visible symbols. First few:")
        for s in sym_res["data"][:5]:
            print(f"  - {s['name']} (Trade Allowed: {s.get('trade_allowed', 'N/A')})")
    else:
        print(f"Error: {sym_res.get('error', 'No symbols found')}")

    print("\n--- Symbol Info (EURUSD) ---")
    eurusd_info_res = get_symbol_info("EURUSD")
    if eurusd_info_res["success"]:
        print(eurusd_info_res["data"])
    else:
        print(f"Error: {eurusd_info_res['error']}")

    print("\n--- Symbol Tick (EURUSD) ---")
    eurusd_tick_res = get_symbol_tick("EURUSD")
    if eurusd_tick_res["success"]:
        print(eurusd_tick_res["data"])
        if eurusd_tick_res.get("error"):
            print(f"  Note: {eurusd_tick_res['error']}")
    else:
        print(f"Error: {eurusd_tick_res['error']}")

    print("\n--- Rates (EURUSD M1, last 5 bars) ---")
    eurusd_rates_res = get_rates("EURUSD", mt5.TIMEFRAME_M1, 0, 5)
    if eurusd_rates_res["success"] and eurusd_rates_res["data"]:
        print(f"Retrieved {len(eurusd_rates_res['data'])} bars.")
        print(pd.DataFrame(eurusd_rates_res["data"]))
    else:
        print(f"Error: {eurusd_rates_res.get('error', 'Failed')}")

    print("\n--- Get Orders (EURUSD) ---")
    orders_res = get_orders(symbol="EURUSD")
    if orders_res["success"]:
        print(f"Found {len(orders_res['data'])} EURUSD orders.")
    else:
        print(f"Error: {orders_res['error']}")

    print("\n--- Get Positions (All) ---")
    pos_res = get_positions()
    if pos_res["success"]:
        print(f"Found {len(pos_res['data'])} open positions.")
    else:
        print(f"Error: {pos_res['error']}")

    print("\n--- Shutting down ---")
    shutdown_mt5()
