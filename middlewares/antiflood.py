from aiogram import BaseMiddleware
from aiogram.types import Message
import time

class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, limit: int):
        super().__init__()
        self.limit = limit
        self.user_timestamps = {}

    async def __call__(self, handler, event: Message, data):
        # Получаем текущее время
        current_time = time.time()
        # Получаем ID пользователя из сообщения
        user_id = event.from_user.id

        # Проверяем, отправлял ли пользователь сообщения ранее
        if user_id in self.user_timestamps:
            # Получаем время последнего сообщения пользователя
            last_message_time = self.user_timestamps[user_id]
            # Если интервал между сообщениями меньше установленного лимита
            if current_time - last_message_time < self.limit:
                # Отправляем предупреждение о флуде и прерываем обработку
                await event.answer("Вы отправляете сообщения слишком быстро.")
                return

        # Обновляем время последнего сообщения пользователя
        self.user_timestamps[user_id] = current_time

        # Передаем управление следующему обработчику
        return await handler(event, data)
