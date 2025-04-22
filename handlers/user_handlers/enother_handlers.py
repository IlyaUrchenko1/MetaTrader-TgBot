from aiogram import Router, F
from aiogram.types import Message

from keyboards.keyboards import get_main_inline_keyboard, get_reply_keyboard

router = Router()

@router.message(F.text == "📚 Помощь")
async def help_button(message: Message):
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

@router.message(F.text == "❓ FAQ")
async def faq_button(message: Message):
    faq_text = (
        "❓ Часто задаваемые вопросы:\n\n"
        "1️⃣ Как начать торговлю?\n"
        "   Нажмите на кнопку 'Начать торговлю' в главном меню\n\n"
        "2️⃣ Как изменить торговый символ?\n"
        "   Перейдите в 'Настройки' → 'Символ'\n\n"
        "3️⃣ Как настроить размер лота?\n"
        "   Перейдите в 'Настройки' → 'Лот'\n\n"
        "4️⃣ Как проверить активные ордера?\n"
        "   Нажмите на кнопку 'Проверить ордера' в главном меню\n\n"
        "5️⃣ Как получить реферальную ссылку?\n"
        "   Перейдите в 'Профиль' → 'Реферальная ссылка'\n\n"
        "🔹 Если нет ответа на ваш вопрос, пожалуйста, обратитесь в поддержку: @любой_username\n"
    )
    await message.answer(faq_text, reply_markup=get_reply_keyboard(), one_time_keyboard=False)

@router.message(F.text == "🏠 Главное меню")
async def main_menu_button(message: Message):
    main_menu_text = (
        "🏠 Главное меню\n\n"
        "Выберите действие из списка ниже:"
    )
    await message.answer(main_menu_text, reply_markup=get_main_inline_keyboard())
