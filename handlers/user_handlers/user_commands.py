from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart

from utils.database import Database
from utils.constants import BOT_USERNAME
from keyboards.keyboards import get_main_inline_keyboard, get_reply_keyboard

router = Router()
db = Database()

@router.message((CommandStart()) or (F.text == "🏠 Главное меню"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username
    full_name = message.from_user.full_name
    referrer_id = None
    
    if len(message.text.split()) > 1:
        try:
            referrer_id = int(message.text.split()[1])
        except ValueError:
            pass
    
    if not db.add_user(user_id, username, full_name, referrer_id):
        await message.answer("Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.")
        return
    
    await message.answer(f"👋 Привет, {full_name}!\n\n"
        "🤖 Я ваш персональный торговый ассистент для MetaTrader 5\n\n", reply_markup=get_reply_keyboard())
    
    welcome_text = (
        f"📊 Что я умею:\n"
        "• Автоматическая торговля по заданным параметрам\n"
        "• Управление ордерами и позициями\n"
        "• Настройка торговых параметров\n"
        "• Мониторинг состояния счета\n\n"
        "💡 Выберите действие в меню ниже:"
    )
    
    await message.answer(welcome_text, reply_markup=get_main_inline_keyboard())
    
    if referrer_id:
        referrer_profile = db.get_user_profile(referrer_id)
        if referrer_profile:
            await message.bot.send_message(
                referrer_id,
                f"🎉 У вас новый реферал!\n"
                f"👤 Пользователь: {full_name}\n"
                f"📱 Username: @{username if username else 'Нет'}"
            )

@router.message(Command("help"))
async def help_command(message: Message):
    help_text = (
        "📚 Справочная информация:\n\n"
        "🔹 Основные команды:\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "get_id - Показать ваш ID\n\n"
        "🔹 Торговые функции:\n"
        "• Начать торговлю - Запуск автоматической торговли\n"
        "• Проверить ордера - Просмотр активных ордеров\n"
        "• Настройки - Изменение параметров торговли\n"
        "• Информация - Просмотр текущей конфигурации\n\n"
        "💡 Для начала работы нажмите /start"
    )
    await message.answer(help_text, reply_markup=get_reply_keyboard())

@router.message(Command("status"))
async def status_command(message: Message):
    status_text = (
        "📊 Статус системы:\n\n"
        "✅ Бот активен и готов к работе\n"
        "🤖 Версия: 1.0.0\n"
        "📅 Последнее обновление: 20.04.2024\n\n"
        "💡 Для начала работы выберите действие в меню"
    )
    await message.answer(status_text, reply_markup=get_reply_keyboard()) 
    
@router.message(F.text == "get_id")
async def get_id_command(message: Message):
    await message.answer(f"ID чата: {message.chat.id}\n"
                         f"ID пользователя: {message.from_user.id}\n")
