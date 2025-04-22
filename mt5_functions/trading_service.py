from typing import List, Dict, Optional, Tuple, Any
import MetaTrader5 as mt5
from mt5_functions import mt5_api

class TradingService:
    def get_account_balance(self) -> Optional[float]:
        account_info = mt5_api.get_account_info()
        if account_info:
            return account_info.get("data", {}).get("balance")
        else:
            print(f"Не удалось получить информацию о счете через mt5_api.")
            return None

    def get_available_symbols(self) -> List[Dict[str, any]]:
        symbols = mt5_api.get_symbols(only_visible=True)
        if not symbols:
            print(f"Не удалось получить список символов через mt5_api.")
            return []
            
        return [
            {
                "name": symbol.name,
                "description": f"{symbol.name} - {symbol.description}",
                "digits": symbol.digits,
                "point": symbol.point,
                "trade_mode": symbol.trade_mode,
                "volume_min": symbol.volume_min,
                "volume_max": symbol.volume_max,
                "volume_step": symbol.volume_step
            }
            for symbol in symbols
        ]

    def select_symbol(self, symbol_name: str) -> Tuple[bool, str]:
        if not mt5_api.select_symbol(symbol_name):
            return False, f"Не удалось выбрать или найти символ {symbol_name} в MT5."
        
        symbol_info = mt5.symbol_info(symbol_name)
        if not symbol_info or not symbol_info.trade_mode:
            return False, f"Торговля по символу {symbol_name} запрещена."
            
        return True, f"Символ {symbol_name} доступен для торговли."

    def get_symbol_info(self, symbol_name: str) -> Optional[Dict]:
        symbol_info = mt5_api.get_symbol_info_detailed(symbol_name)
        if symbol_info is None:
             print(f"Не удалось получить информацию о символе {symbol_name} через mt5_api.")
             return None
            
        return {
            "name": symbol_info.name,
            "description": symbol_info.description,
            "digits": symbol_info.digits,
            "point": symbol_info.point,
            "trade_mode": symbol_info.trade_mode,
            "volume_min": symbol_info.volume_min,
            "volume_max": symbol_info.volume_max,
            "volume_step": symbol_info.volume_step,
            "spread": symbol_info.spread,
            "spread_float": symbol_info.spread_float,
            "trade_stops_level": symbol_info.trade_stops_level,
            "filling_mode": symbol_info.filling_mode,
            "visible": symbol_info.visible,
        }

    def get_grid_status(self, symbol: str, magic_number: int) -> Dict[str, Any]:
        try:
            orders_raw = mt5_api.get_active_orders(symbol, magic_number)
            positions_raw = mt5_api.get_open_positions(symbol, magic_number)

            orders_list = [
                {
                    "ticket": order.ticket,
                    "type": mt5_api.order_type_string(order.type),
                    "price_open": order.price_open,
                    "volume_initial": order.volume_initial,
                    "symbol": order.symbol,
                    "magic": order.magic
                }
                for order in orders_raw
            ]
            positions_list = [
                {
                    "ticket": pos.ticket,
                    "type": mt5_api.position_type_string(pos.type),
                    "price_open": pos.price_open,
                    "volume": pos.volume,
                    "profit": pos.profit,
                    "symbol": pos.symbol,
                    "magic": pos.magic
                }
                for pos in positions_raw
            ]

            return {
                "success": True,
                "orders": orders_list,
                "positions": positions_list,
                "error": None
            }
        except Exception as e:
            error_msg = f"Ошибка получения статуса сетки ({symbol}/{magic_number}): {e}"
            print(error_msg)
            return {
                "success": False,
                "orders": [],
                "positions": [],
                "error": error_msg
            }

    def place_initial_grid(
        self,
        symbol: str,
        distance_pips: int,
        lot: float,
        percent: float,
        magic_number: int
    ) -> Tuple[bool, str]:
        symbol_ok, message = self.select_symbol(symbol)
        if not symbol_ok:
            return False, message

        current_balance = self.get_account_balance()
        if current_balance is None:
            return False, "Не удалось получить баланс счета."

        # Calculate lot size based on account balance and risk percentage
        symbol_info = mt5_api.get_symbol_info(symbol)
        if not symbol_info["success"] or not symbol_info["data"]:
            return False, f"Не удалось получить информацию о символе {symbol}."
            
        volume_step = symbol_info["data"].get("volume_step", 0.01)
        calculated_lot = round((current_balance * percent / 100 * lot) / volume_step) * volume_step
        
        if calculated_lot <= 0:
            calculated_lot = 0.01
            
        print(f"Рассчитанный лот для {symbol}: {calculated_lot}")

        try:
            buy_result = self._place_buy_stop_order(symbol, distance_pips, calculated_lot, magic_number)
            sell_result = self._place_sell_stop_order(symbol, distance_pips, calculated_lot, magic_number)
            
            order_results = {
                "buy": buy_result,
                "sell": sell_result
            }
        except Exception as e:
            return False, f"Ошибка при размещении ордеров: {e}"

        buy_result = order_results.get("buy", {})
        sell_result = order_results.get("sell", {})

        success = buy_result.get("success", False) and sell_result.get("success", False)
        message = f"Результат установки сетки для {symbol} (Лот: {calculated_lot}, Дист: {distance_pips} пипсов, Magic: {magic_number}):\n"
        message += f"  BuyStop: {buy_result.get('message', 'Нет данных')}\n"
        message += f"  SellStop: {sell_result.get('message', 'Нет данных')}"

        if not success:
            message += "\n\n⚠️ Не все ордера были установлены успешно."

        return success, message

    def _place_buy_stop_order(self, symbol: str, distance_pips: int, lot_size: float, magic_number: int) -> Dict[str, Any]:
        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return {"success": False, "message": f"Не удалось получить информацию о символе {symbol}"}
            
            point = symbol_info.point
            digits = symbol_info.digits
            current_price = mt5.symbol_info_tick(symbol).ask
            
            price = current_price + (distance_pips * 10 * point)
            price = round(price, digits)
            
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": lot_size,
                "type": mt5.ORDER_TYPE_BUY_STOP,
                "price": price,
                "deviation": 20,
                "magic": magic_number,
                "comment": f"BuyStop Grid {magic_number}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_RETURN,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return {"success": True, "message": f"Ордер BuyStop размещен по цене {price}"}
            else:
                return {"success": False, "message": f"Ошибка размещения BuyStop: {result.retcode}"}
        except Exception as e:
            return {"success": False, "message": f"Исключение при размещении BuyStop: {e}"}

    def _place_sell_stop_order(self, symbol: str, distance_pips: int, lot_size: float, magic_number: int) -> Dict[str, Any]:
        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return {"success": False, "message": f"Не удалось получить информацию о символе {symbol}"}
            
            point = symbol_info.point
            digits = symbol_info.digits
            current_price = mt5.symbol_info_tick(symbol).bid
            
            price = current_price - (distance_pips * 10 * point)
            price = round(price, digits)
            
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": lot_size,
                "type": mt5.ORDER_TYPE_SELL_STOP,
                "price": price,
                "deviation": 20,
                "magic": magic_number,
                "comment": f"SellStop Grid {magic_number}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_RETURN,
            }
            
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                return {"success": True, "message": f"Ордер SellStop размещен по цене {price}"}
            else:
                return {"success": False, "message": f"Ошибка размещения SellStop: {result.retcode}"}
        except Exception as e:
            return {"success": False, "message": f"Исключение при размещении SellStop: {e}"}

    def close_grid(self, symbol: str, magic_number: int) -> Tuple[bool, str, List[str]]:
        symbol_ok, msg = self.select_symbol(symbol)
        if not symbol_ok:
            print(f"Предупреждение при закрытии сетки: {msg}")
        
        report = mt5_api.close_positions_and_orders(symbol, magic_number)
        
        success = report.get("status") == "success"
        message = report.get("message", "Не удалось получить сообщение о закрытии.")
        details = report.get("details", [])
        
        return success, message, details