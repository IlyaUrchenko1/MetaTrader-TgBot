ADMIN_IDS = {7814530746}  # ID администраторов бота

BOT_USERNAME = "MetaTrader10_bot"  # Имя бота в Telegram

# Параметры торговли
SYMBOL = "USDJPY"  # Торговый инструмент
LOT = 0.01  # Размер лота
PERCENT = 1.0  # Процент от баланса для расчета лота
K_LOT = 2.0  # Множитель для увеличения лота
DISTANCE_PIPS = 50  # Расстояние до ордеров в пипсах
TRAILING_START = 20  # Расстояние для начала трейлинга
TRAILING_DISTANCE = 15  # Расстояние трейлинга
MAX_DRAWDOWN_PCT = 30  # Максимальная просадка в процентах
MAGIC_NUMBER = 123456  # Идентификатор эксперта
DISTANCE = 100
LOT_BY_BALANCE = 2.0
LOT_MULTIPLIER = 2.0

def update_symbol(new_symbol: str) -> bool:
    """Обновляет торговый символ"""
    global SYMBOL
    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            return False
        symbol_info = mt5.symbol_info(new_symbol)
        if symbol_info is None or not symbol_info.visible:
            return False
        SYMBOL = new_symbol
        return True
    except Exception:
        return False
