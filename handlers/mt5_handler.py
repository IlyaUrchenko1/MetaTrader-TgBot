import MetaTrader5 as mt5
from aiogram.fsm.state import State, StatesGroup
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from keyboards.keyboards import get_main_inline_keyboard, get_back_keyboard, get_orders_keyboard, get_settings_keyboard, get_profile_keyboard, get_symbols_keyboard, get_back_keyboard_profile
from utils.database import Database
from mt5_functions.trading_service import TradingService
from utils.constants import ADMIN_IDS
from mt5_functions.mt5_api import get_orders, get_positions

router = Router()
db = Database()
trading_service = TradingService()

class GridState(StatesGroup):
    grid_active = State()

@router.callback_query(F.data == "start_grid")
async def cmd_start_grid(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.answer("⛔ У вас нет прав для выполнения этой команды.")
        await callback.answer()
        return

    await callback.message.edit_text("🚀 Запуск сеточной стратегии...")
    
    mt5.initialize()
    
    user_id = callback.from_user.id
    user_profile = db.get_user_profile(user_id)
    
    if not user_profile:
        db.add_user(user_id, callback.from_user.username, callback.from_user.full_name)
        user_profile = db.get_user_profile(user_id)
    
    user_settings = user_profile.get("settings", {})
    if not user_settings:
        await callback.message.edit_text("❌ Ошибка: Настройки пользователя не найдены. Пожалуйста, настройте профиль.", reply_markup=get_main_inline_keyboard())
        await callback.answer()
        return
        
    symbol = user_settings.get("symbol")
    distance_pips = user_settings.get("distance_pips")
    lot = user_settings.get("lot")
    
    if not all([symbol, isinstance(distance_pips, (int, float)), isinstance(lot, (int, float))]):
         await callback.message.edit_text(
             f"❌ Ошибка: Не все необходимые настройки сетки заданы.\n" 
             f"Требуется: Символ ({symbol}), Дистанция ({distance_pips}), Лот ({lot}).\n"
             f"Пожалуйста, проверьте настройки.",
             reply_markup=get_settings_keyboard()
         )
         await callback.answer()
         return

    magic_number = user_id + 1000
    
    await state.update_data(
        grid_symbol=symbol,
        grid_distance=distance_pips,
        grid_lot=lot,
        grid_magic=magic_number
    )
    
    await callback.message.edit_text(
        f"📊 Параметры сетки:\n"
        f"Символ: {symbol}\n"
        f"Дистанция: {distance_pips} пипсов\n"
        f"Лот: {lot}\n"
        f"Magic Number: {magic_number}\n\n"
        f"⏳ Устанавливаем сетку..."
    )
    
    success, result_message = trading_service.place_initial_grid(
        symbol=symbol,
        distance_pips=int(distance_pips),
        lot=float(lot),
        percent=0.0,
        magic_number=magic_number
    )
    
    await callback.message.edit_text(result_message)
    
    if success:
        await callback.message.answer("✅ Сетка успешно установлена. Мониторинг запущен. Используйте /grid_status для проверки и /stop_grid для остановки.", reply_markup=get_main_inline_keyboard())
        await state.set_state(GridState.grid_active)
    else:
        await callback.message.answer(f"❌ Не удалось установить сетку. Причина: {result_message}. Попробуйте снова или проверьте настройки.", reply_markup=get_main_inline_keyboard())
        await state.clear()
    
    await callback.answer()

@router.callback_query(F.data == "status")
async def check_status(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.message.answer("⛔ У вас нет прав для выполнения этой команды.")
        await callback.answer()
        return
    
    current_state = await state.get_state()
    if current_state != GridState.grid_active:
        await callback.message.answer("Сетка не активна. Запустите ее через меню 'Открыть сетку'.", reply_markup=get_main_inline_keyboard())
        await callback.answer()
        return
    
    user_data = await state.get_data()
    symbol = user_data.get('grid_symbol')
    magic = user_data.get('grid_magic')

    if not symbol or not magic:
        await callback.message.answer("Ошибка: не найдены параметры активной сетки. Попробуйте перезапустить через 'Открыть сетку'.", reply_markup=get_main_inline_keyboard())
        await state.clear()
        await callback.answer()
        return

    await callback.message.edit_text(f"⏳ Получение статуса сетки {symbol} / {magic}...")

    status_result = trading_service.get_grid_status(symbol, magic)

    if not status_result["success"]:
        await callback.message.edit_text(f"❌ Ошибка при получении статуса: {status_result.get('error', 'Неизвестная ошибка')}", reply_markup=get_back_keyboard())
        await callback.answer()
        return

    orders = status_result.get("orders", [])
    positions = status_result.get("positions", [])

    report = f"📊 Статус сетки ({symbol} / Magic: {magic})\n\n"

    if not orders and not positions:
        report += "ℹ️ Активных ордеров и позиций по этой сетке нет."
    else:
        if positions:
            report += "📈 Открытые позиции:\n"
            total_profit = 0.0
            for pos in positions:
                report += f" - Тикет: {pos['ticket']}, Тип: {pos['type']}, Лот: {pos['volume']}, Цена: {pos['price_open']}, Profit: {pos['profit']:.2f}\n"
                total_profit += pos['profit']
            report += f"\n💰 Общий профит позиций: {total_profit:.2f}\n\n"
        else:
            report += "ℹ️ Открытых позиций нет.\n\n"
            
        if orders:
            report += "⏳ Отложенные ордера:\n"
            for order in orders:
                report += f" - Тикет: {order['ticket']}, Тип: {order['type']}, Лот: {order['volume_initial']}, Цена: {order['price_open']}\n"
        else:
            report += "ℹ️ Активных отложенных ордеров нет.\n"

    await callback.message.edit_text(report, reply_markup=get_orders_keyboard(orders, positions))
    await callback.answer()

@router.callback_query(F.data == "show_orders")
async def show_orders(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    symbol = user_data.get('grid_symbol')
    magic = user_data.get('grid_magic')
    
    if not symbol or not magic:
        await callback.message.edit_text("Ошибка: не найдены параметры активной сетки.", reply_markup=get_main_inline_keyboard())
        await callback.answer()
        return
    
    await callback.message.edit_text(f"⏳ Получение активных ордеров для {symbol} / {magic}...")
    
    orders_result = get_orders(symbol=symbol, magic=magic)
    
    if not orders_result["success"]:
        await callback.message.edit_text(f"❌ Ошибка при получении ордеров: {orders_result.get('error', 'Неизвестная ошибка')}", reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    orders = orders_result.get("data", [])
    
    positions_result = get_positions(symbol=symbol, magic=magic)
    positions = positions_result.get("data", []) if positions_result["success"] else []
        
    if not orders:
        await callback.message.edit_text("Нет активных ордеров.", reply_markup=get_orders_keyboard([], positions))
        await callback.answer()
        return
        
    report = "📋 Активные ордера:\n\n"
    for order in orders:
        report += f"Тикет: {order['ticket']}\nТип: {order['type']}\nСимвол: {order['symbol']}\nЛот: {order['volume_initial']}\nЦена: {order['price_open']}\n\n"
        
    await callback.message.edit_text(report, reply_markup=get_orders_keyboard(orders, positions))
    await callback.answer()

@router.callback_query(F.data == "show_positions")
async def show_positions(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    symbol = user_data.get('grid_symbol')
    magic = user_data.get('grid_magic')
    
    if not symbol or not magic:
        await callback.message.edit_text("Ошибка: не найдены параметры активной сетки.", reply_markup=get_main_inline_keyboard())
        await callback.answer()
        return
    
    await callback.message.edit_text(f"⏳ Получение открытых позиций для {symbol} / {magic}...")
    
    positions_result = get_positions(symbol=symbol, magic=magic)
    
    if not positions_result["success"]:
        await callback.message.edit_text(f"❌ Ошибка при получении позиций: {positions_result.get('error', 'Неизвестная ошибка')}", reply_markup=get_back_keyboard())
        await callback.answer()
        return
    
    positions = positions_result.get("data", [])
    
    orders_result = get_orders(symbol=symbol, magic=magic)
    orders = orders_result.get("data", []) if orders_result["success"] else []
        
    if not positions:
        await callback.message.edit_text("Нет открытых позиций.", reply_markup=get_orders_keyboard(orders, []))
        await callback.answer()
        return
        
    report = "📊 Открытые позиции:\n\n"
    total_profit = 0.0
    for pos in positions:
        report += f"Тикет: {pos['ticket']}\nТип: {pos['type']}\nСимвол: {pos['symbol']}\nЛот: {pos['volume']}\nЦена: {pos['price_open']}\nПрофит: {pos['profit']:.2f}\n\n"
        total_profit += pos['profit']
    report += f"\n💰 Общий профит: {total_profit:.2f}"

    await callback.message.edit_text(report, reply_markup=get_orders_keyboard(orders, positions))
    await callback.answer()

@router.callback_query(F.data == "close_all")
async def close_all(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    symbol = user_data.get('grid_symbol')
    magic = user_data.get('grid_magic')
    
    if not symbol or not magic:
        await callback.message.edit_text("Ошибка: не найдены параметры активной сетки.", reply_markup=get_main_inline_keyboard())
        await callback.answer()
        return
    
    await callback.message.edit_text(f"⏳ Закрытие всех позиций и ордеров для {symbol} / {magic}...")
    
    try:
        success, result_message, details_log = trading_service.close_grid(symbol, magic)
        
        full_message = f"{result_message}\n\n"
        if details_log:
            full_message += "Детали операции:\n" + "\n".join(details_log)
            if len(full_message) > 4000:
                full_message = full_message[:4000] + "... (лог усечен)"

        await callback.message.edit_text(full_message, reply_markup=get_main_inline_keyboard())
        
        if success:
            await state.clear()
            await callback.message.answer("Сетка успешно закрыта.")
        else:
             await callback.message.answer("Во время закрытия сетки возникли ошибки. Проверьте лог выше.")

    except Exception as e:
        await callback.message.edit_text(f"Критическая ошибка при закрытии сетки: {e}", reply_markup=get_back_keyboard())
    
    await callback.answer()

@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("⚙️ Настройки", reply_markup=get_settings_keyboard())
    await callback.answer()

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    user_profile = db.get_user_profile(user_id)
    if not user_profile:
        db.add_user(user_id, callback.from_user.username, callback.from_user.full_name)
        user_profile = db.get_user_profile(user_id)
    
    profile_text = f"👤 Профиль\n\nID: {user_id}\nИмя: {callback.from_user.full_name}"
    settings = user_profile.get('settings', {})
    profile_text += f"\n\nТекущие настройки сетки:\nСимвол: {settings.get('symbol', 'Не задан')}\nДистанция: {settings.get('distance_pips', 'Не задана')} пипсов\nЛот: {settings.get('lot', 'Не задан')}"
    
    await callback.message.edit_text(profile_text, reply_markup=get_profile_keyboard())
    await callback.answer()

@router.callback_query(F.data == "select_symbol")
async def select_symbol(callback: CallbackQuery, state: FSMContext):
    symbols_data = trading_service.get_available_symbols()
    if not symbols_data:
        await callback.message.edit_text("Не удалось получить список символов от MT5.", reply_markup=get_settings_keyboard())
        await callback.answer()
        return
        
    symbol_names = [s['name'] for s in symbols_data]
    await callback.message.edit_text("📈 Выберите символ:", reply_markup=get_symbols_keyboard(symbol_names))
    await callback.answer()

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🏠 Главное меню", reply_markup=get_main_inline_keyboard())
    await callback.answer()

@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: CallbackQuery, state: FSMContext):
    await show_profile(callback, state)

@router.callback_query(F.data.startswith("symbol_"))
async def handle_symbol_selection(callback: CallbackQuery, state: FSMContext):
    symbol = callback.data.split("symbol_", 1)[1]
    user_id = callback.from_user.id

    is_tradable, message = trading_service.select_symbol(symbol)
    if not is_tradable:
         await callback.message.edit_text(f"❌ Ошибка: {message}", reply_markup=get_settings_keyboard())
         await callback.answer()
         return

    try:
        db.update_user_setting(user_id, "symbol", symbol)
        await callback.message.edit_text(f"✅ Символ {symbol} успешно установлен.", reply_markup=get_settings_keyboard())
    except Exception as e:
        await callback.message.edit_text(f"❌ Ошибка сохранения символа в БД: {e}", reply_markup=get_settings_keyboard())
        
    await callback.answer()