from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from bot.adapters.base import TMAdapter
from bot.config import Config


class InjectMiddleware(BaseMiddleware):
    def __init__(self, adapter: TMAdapter, config: Config):
        self._adapter = adapter
        self._config = config

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        # Проверка доступа
        user = data.get("event_from_user")
        if user and user.id not in self._config.allowed_ids:
            return

        data["adapter"] = self._adapter
        data["config"] = self._config
        return await handler(event, data)
