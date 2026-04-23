import asyncio
import logging
from aiogram import Bot, Dispatcher
from bot.config import Config
from bot.adapters import make_adapter

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    config = Config.load()
    adapter = make_adapter(config)

    bot = Bot(token=config.bot_token)
    dp = Dispatcher()

    # Импорт и регистрация роутеров
    from bot.handlers.common import router as common_router
    from bot.handlers.help_handler import router as help_router
    from bot.handlers.list_handler import router as list_router
    from bot.handlers.manage_handler import router as manage_router
    from bot.handlers.add_handler import router as add_router
    from bot.handlers.credentials_handler import router as creds_router
    from bot.handlers.settings_handler import router as settings_router
    from bot.handlers.errors_handler import router as errors_router
    from bot.middleware import InjectMiddleware

    dp.message.middleware(InjectMiddleware(adapter, config))
    dp.callback_query.middleware(InjectMiddleware(adapter, config))

    # common должен быть первым — /cancel работает до FSM-хендлеров
    dp.include_router(common_router)
    dp.include_router(help_router)
    dp.include_router(list_router)
    dp.include_router(manage_router)
    dp.include_router(add_router)
    dp.include_router(creds_router)
    dp.include_router(settings_router)
    dp.include_router(errors_router)

    from bot.notifier import run_notifier

    logger.info("Bot starting (adapter=%s)", config.tm_adapter)
    asyncio.create_task(run_notifier(bot, adapter, config))
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
