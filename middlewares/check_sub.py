from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.constants import ADMIN_IDS


class CheckSubscriptionMiddleware(BaseMiddleware):
    """Middleware для проверки подписки пользователя на канал."""
    
    def __init__(self, bot: Bot):
        """
        Инициализация middleware.
        
        Args:
            bot: Экземпляр бота для проверки подписки
        """
        super().__init__()
        self.bot = bot
        self.channel_id = -1002409743489
        self.channel_username = "AraStarsCommunity"
        self.allowed_statuses = ["member", "administrator", "creator"]
        
    async def __call__(
        self,
        handler,
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        user_id = event.from_user.id
        
        if user_id in ADMIN_IDS:
            return await handler(event, data)
        
        is_subscribed = await self._check_subscription(user_id)
        if is_subscribed:
            return await handler(event, data)
        
        await self._send_subscription_notification(event)
        return None
    
    async def _check_subscription(self, user_id: int) -> bool:
        try:
            member = await self.bot.get_chat_member(chat_id=self.channel_id, user_id=user_id)
            return member.status in self.allowed_statuses
        except Exception:
            return False
    
    async def _send_subscription_notification(self, event: Union[Message, CallbackQuery]) -> None:
        """
        Отправляет уведомление о необходимости подписки.
        
        Args:
            event: Событие (сообщение или callback)
        """
        # Создаем клавиатуру с кнопкой подписки
        builder = InlineKeyboardBuilder()
        builder.button(
            text="📢 Подписаться на канал",
            url=f"t.me/{self.channel_username}"
        )
        
        notification_text = "❗ Для использования бота необходимо подписаться на наш канал. Подпишитесь и снова введите /start"
        
        # Отправляем уведомление в зависимости от типа события
        if isinstance(event, CallbackQuery):
            await event.answer()
            await event.message.answer(
                notification_text,
                reply_markup=builder.as_markup()
            )
        else:
            await event.answer(
                notification_text,
                reply_markup=builder.as_markup()
            )
