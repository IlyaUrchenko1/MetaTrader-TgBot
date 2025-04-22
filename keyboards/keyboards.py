from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_reply_keyboard() -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="📚 Помощь"),
            KeyboardButton(text="❓ FAQ")
        ],
        [
            KeyboardButton(text="🏠 Главное меню")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=False)



def get_main_inline_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="🚀 Открыть сетку", callback_data="start_grid"),
            InlineKeyboardButton(text="🔄 Проверить ордера", callback_data="status")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile")
        ],
        [
            InlineKeyboardButton(text="📈 Выбрать символ", callback_data="select_symbol")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_settings_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="📈 Символ", callback_data="setting_symbol"),
            InlineKeyboardButton(text="💰 Лот", callback_data="setting_lot")
        ],
        [
            InlineKeyboardButton(text="📏 Расстояние", callback_data="setting_distance"),
            InlineKeyboardButton(text="🎯 Трейлинг", callback_data="setting_trailing")
        ],
        [
            InlineKeyboardButton(text="⚠️ Просадка", callback_data="setting_drawdown"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_profile_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="👥 Рефералы", callback_data="referrals"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
            InlineKeyboardButton(text="🔗 Реферальная ссылка", callback_data="ref_link")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_symbols_keyboard(symbols: list) -> InlineKeyboardMarkup:
    keyboard = []
    row = []
    
    for symbol in symbols:
        row.append(InlineKeyboardButton(
            text=symbol["name"],
            callback_data=f"symbol_{symbol['name']}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_keyboard() -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 

def get_back_keyboard_profile() -> InlineKeyboardMarkup:
    keyboard = [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_profile")]]
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 

def get_orders_keyboard(orders: list, positions: list) -> InlineKeyboardMarkup:
    keyboard = []
    
    if orders:
        keyboard.append([InlineKeyboardButton(text="📌 Активные ордера", callback_data="show_orders")])
    
    if positions:
        keyboard.append([InlineKeyboardButton(text="💰 Открытые позиции", callback_data="show_positions")])
    
    if orders or positions:
        keyboard.append([InlineKeyboardButton(text="❌ Закрыть все", callback_data="close_all")])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 