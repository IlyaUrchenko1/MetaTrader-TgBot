from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from utils.database import Database
from utils.constants import BOT_USERNAME
from keyboards.keyboards import (
    get_profile_keyboard, 
    get_settings_keyboard, 
    get_main_inline_keyboard, 
    get_back_keyboard,
    get_back_keyboard_profile
)

router = Router()
db = Database()

class SettingsState(StatesGroup):
    waiting_for_symbol = State()
    waiting_for_lot = State()
    waiting_for_distance = State()
    waiting_for_trailing = State()
    waiting_for_drawdown = State()

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    profile = db.get_user_profile(user_id)
    
    if not profile:
        await callback.answer("Произошла ошибка при получении профиля")
        return
    
    referral_stats = db.get_referral_stats(user_id)
    
    text = (
        f"👤 Ваш профиль:\n\n"
        f"📊 Статистика:\n"
        f"• Успешных сделок: {profile['successful_trades']}\n"
        f"• Неудачных сделок: {profile['failed_trades']}\n"
        f"• Общий профит: {profile['total_profit']:.2f}\n\n"
        f"👥 Реферальная система:\n"
        f"• Приглашено пользователей: {referral_stats['total_referrals']}\n"
        f"• Заработано с рефералов: {profile['referral_earnings']:.2f}\n\n"
        f"🔗 Ваша реферальная ссылка:\n"
        f"https://t.me/{BOT_USERNAME}?start={user_id}"
    )
    
    await callback.message.edit_text(text, reply_markup=get_profile_keyboard())
    await callback.answer()

@router.callback_query(F.data == "referrals")
async def show_referrals(callback: CallbackQuery):
    user_id = callback.from_user.id
    referral_stats = db.get_referral_stats(user_id)
    
    if referral_stats['total_referrals'] == 0:
        text = "У вас пока нет рефералов. Пригласите друзей по вашей реферальной ссылке!"
    else:
        text = (
            f"👥 Ваши рефералы:\n\n"
            f"• Всего рефералов: {referral_stats['total_referrals']}\n"
            f"• Активных рефералов: {referral_stats['active_referrals']}\n\n"
            f"Приглашайте больше друзей по вашей реферальной ссылке!"
        )
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard_profile())
    await callback.answer()

@router.callback_query(F.data == "stats")
async def show_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    profile = db.get_user_profile(user_id)
    
    if not profile:
        await callback.answer("Произошла ошибка при получении статистики")
        return
    
    total_trades = profile['successful_trades'] + profile['failed_trades']
    winrate = (profile['successful_trades'] / total_trades * 100) if total_trades > 0 else 0
    avg_profit = (profile['total_profit'] / profile['successful_trades']) if profile['successful_trades'] > 0 else 0
    
    text = (
        f"📊 Ваша статистика:\n\n"
        f"• Всего сделок: {total_trades}\n"
        f"• Успешных сделок: {profile['successful_trades']}\n"
        f"• Неудачных сделок: {profile['failed_trades']}\n"
        f"• Винрейт: {winrate:.2f}%\n"
        f"• Общий профит: {profile['total_profit']:.2f}\n"
        f"• Средний профит: {avg_profit:.2f}\n"
    )
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard_profile())
    await callback.answer()

@router.callback_query(F.data == "ref_link")
async def copy_ref_link(callback: CallbackQuery):
    user_id = callback.from_user.id
    ref_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    
    text = (
        f"🔗 Ваша реферальная ссылка:\n\n"
        f"{ref_link}\n\n"
        f"Поделитесь этой ссылкой с друзьями и получайте бонусы за каждого приглашенного пользователя!"
    )
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard_profile())

@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery):
    user_id = callback.from_user.id
    profile = db.get_user_profile(user_id)
    
    if not profile:
        await callback.answer("Произошла ошибка при получении настроек")
        return
    
    settings = profile['settings']
    text = (
        f"⚙️ Текущие настройки:\n\n"
        f"📈 Символ: {settings['symbol']}\n"
        f"💰 Лот: {settings['lot']}\n"
        f"📏 Расстояние: {settings['distance_pips']}\n"
        f"🎯 Трейлинг: {settings['trailing_distance']}\n"
        f"⚠️ Просадка: {settings['max_drawdown_pct']}%"
    )
    
    await callback.message.edit_text(text, reply_markup=get_settings_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("setting_"))
async def setting_selected(callback: CallbackQuery, state: FSMContext):
    setting_type = callback.data.split("_")[1]
    await state.set_state(getattr(SettingsState, f"waiting_for_{setting_type}"))
    await state.update_data(message_id=callback.message.message_id)
    
    messages = {
        "symbol": "Введите новый символ (например, EURUSD, BTCUSD):",
        "lot": "Введите новый размер лота (от 0.01 до 100):",
        "distance": "Введите новое расстояние в пипсах (от 1 до 1000):",
        "trailing": "Введите новое значение трейлинга (от 1 до 100):",
        "drawdown": "Введите новый процент максимальной просадки (от 1 до 100%):"
    }
    
    text = messages.get(setting_type, f"Введите новое значение для {setting_type}:")
    
    await callback.message.edit_text(text, reply_markup=get_back_keyboard())
    await callback.answer()

@router.message(SettingsState.waiting_for_symbol)
async def process_symbol(message: Message, state: FSMContext):
    symbol = message.text.upper()
    user_id = message.from_user.id
    
    if db.update_user_settings(user_id, {"symbol": symbol}):
        await message.answer("✅ Символ успешно обновлен")
        await show_updated_settings(message, user_id, state)
    else:
        await message.answer("❌ Ошибка при обновлении символа")
        await state.clear()

@router.message(SettingsState.waiting_for_lot)
async def process_lot(message: Message, state: FSMContext):
    try:
        lot = float(message.text)
        user_id = message.from_user.id
        
        if 0.01 <= lot <= 100:
            if db.update_user_settings(user_id, {"lot": lot}):
                await message.answer("✅ Лот успешно обновлен")
                await show_updated_settings(message, user_id, state)
            else:
                await message.answer("❌ Ошибка при обновлении лота")
                await state.clear()
        else:
            await message.answer("❌ Лот должен быть от 0.01 до 100")
    except ValueError:
        await message.answer("❌ Введите корректное число")
        await state.clear()

@router.message(SettingsState.waiting_for_distance)
async def process_distance(message: Message, state: FSMContext):
    try:
        distance = int(message.text)
        user_id = message.from_user.id
        
        if 1 <= distance <= 1000:
            if db.update_user_settings(user_id, {"distance_pips": distance}):
                await message.answer("✅ Расстояние успешно обновлено")
                await show_updated_settings(message, user_id, state)
            else:
                await message.answer("❌ Ошибка при обновлении расстояния")
                await state.clear()
        else:
            await message.answer("❌ Расстояние должно быть от 1 до 1000")
    except ValueError:
        await message.answer("❌ Введите корректное число")
        await state.clear()

@router.message(SettingsState.waiting_for_trailing)
async def process_trailing(message: Message, state: FSMContext):
    try:
        trailing = int(message.text)
        user_id = message.from_user.id
        
        if 1 <= trailing <= 100:
            if db.update_user_settings(user_id, {"trailing_distance": trailing}):
                await message.answer("✅ Трейлинг успешно обновлен")
                await show_updated_settings(message, user_id, state)
            else:
                await message.answer("❌ Ошибка при обновлении трейлинга")
                await state.clear()
        else:
            await message.answer("❌ Трейлинг должен быть от 1 до 100")
    except ValueError:
        await message.answer("❌ Введите корректное число")
        await state.clear()

@router.message(SettingsState.waiting_for_drawdown)
async def process_drawdown(message: Message, state: FSMContext):
    try:
        drawdown = int(message.text)
        user_id = message.from_user.id
        
        if 1 <= drawdown <= 100:
            if db.update_user_settings(user_id, {"max_drawdown_pct": drawdown}):
                await message.answer("✅ Просадка успешно обновлена")
                await show_updated_settings(message, user_id, state)
            else:
                await message.answer("❌ Ошибка при обновлении просадки")
                await state.clear()
        else:
            await message.answer("❌ Просадка должна быть от 1 до 100%")
    except ValueError:
        await message.answer("❌ Введите корректное число")
        await state.clear()

async def show_updated_settings(message: Message, user_id: int, state: FSMContext):
    profile = db.get_user_profile(user_id)
    await state.clear()
    
    if not profile:
        await message.answer("Произошла ошибка при получении обновленных настроек")
        return
    
    settings = profile['settings']
    text = (
        f"⚙️ Обновленные настройки:\n\n"
        f"📈 Символ: {settings['symbol']}\n"
        f"💰 Лот: {settings['lot']}\n"
        f"📏 Расстояние: {settings['distance_pips']}\n"
        f"🎯 Трейлинг: {settings['trailing_distance']}\n"
        f"⚠️ Просадка: {settings['max_drawdown_pct']}%"
    )
    
    await message.answer(text, reply_markup=get_settings_keyboard())

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Главное меню", reply_markup=get_main_inline_keyboard())
    await callback.answer()

@router.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await show_profile(callback)