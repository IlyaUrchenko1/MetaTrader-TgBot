import asyncio
import os
from typing import Optional, Union, Dict, Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

from middlewares.antiflood import AntiFloodMiddleware
from middlewares.private_chat import PrivateChatMiddleware
from middlewares.work_set import WorkSetMiddleware

from handlers.user_handlers.user_commands import router as user_router
from handlers.user_handlers.profile_settings import router as profile_router
from handlers.mt5_handler import router as mt5_router
from handlers.user_handlers.enother_handlers import router as enother_router
load_dotenv()

default_setting = DefaultBotProperties(parse_mode='HTML')
bot = Bot(os.getenv("BOT_TOKEN"), default=default_setting)
dp = Dispatcher()

async def main() -> None:
    dp.message.middleware(PrivateChatMiddleware())
    dp.message.middleware(AntiFloodMiddleware(limit=0.5))
    dp.message.middleware(WorkSetMiddleware())

    dp.include_routers(user_router, profile_router, mt5_router, enother_router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        print("Бот стартовал :)")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен :(")
    except Exception as e:
        print(f"Произошла ошибка: {e}")