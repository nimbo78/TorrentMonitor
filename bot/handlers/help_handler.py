from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

router = Router()

HELP_TEXT = (
    "👋 <b>TorrentMonitor Bot</b>\n\n"
    "Управление раздачами TorrentMonitor прямо из Telegram.\n\n"
    "<b>Команды:</b>\n"
    "📋 /list — список отслеживаемых раздач\n"
    "🔗 /addurl — добавить раздачу по URL\n"
    "📺 /addserial — добавить сериал по названию\n"
    "🔑 /credentials — учётные данные трекеров\n"
    "⚙️ /settings — настройки TorrentMonitor\n"
    "⚠️ /errors — последние ошибки\n"
    "❓ /help — эта справка\n\n"
    "<i>Уведомления о новых раздачах приходят автоматически.</i>"
)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(HELP_TEXT, parse_mode="HTML")


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, parse_mode="HTML")
