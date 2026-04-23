from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from bot.adapters.base import TMAdapter
from bot.config import Config

router = Router()


def close_button(text: str = "✖️ Закрыть") -> InlineKeyboardButton:
    """Стандартная кнопка удаления текущего сообщения."""
    return InlineKeyboardButton(text=text, callback_data="close")


def _close_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[close_button()]])


@router.callback_query(F.data == "close")
async def cb_close(call: CallbackQuery):
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.answer()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current = await state.get_state()
    if current is None:
        await message.answer("Нечего отменять.")
        return
    await state.clear()
    await message.answer("✅ Отменено.")


@router.message(Command("status"))
async def cmd_status(message: Message):
    from bot.notifier import get_health, read_last_seen

    health = get_health()
    last_seen = health.get("last_seen") or read_last_seen()
    last_poll_at = health.get("last_poll_at") or "—"
    ok_flag = health.get("last_poll_ok")
    if ok_flag is True:
        status = "✅ OK"
    elif ok_flag is False:
        status = "⚠️ error"
    else:
        status = "⏳ ещё не опрашивал"
    count = health.get("last_count", 0)
    error = health.get("last_error") or "—"

    text = (
        "📊 <b>Статус нотификатора</b>\n\n"
        f"Последний <code>last_seen</code>: <code>{last_seen}</code>\n"
        f"Последний опрос: <code>{last_poll_at}</code>\n"
        f"Результат: {status}\n"
        f"Найдено в последний раз: <b>{count}</b>\n"
        f"Ошибка: {error}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=_close_kb())


@router.message(Command("poll"))
async def cmd_poll(message: Message, adapter: TMAdapter, config: Config):
    """Ручной диагностический опрос — не мутирует state, не шлёт уведомления."""
    from bot.notifier import read_last_seen

    since = read_last_seen()
    try:
        r = await adapter.get_new_items(since)
    except Exception as e:
        await message.answer(
            f"🔍 <b>Опрос выполнен</b>\nsince: <code>{since}</code>\n"
            f"ошибка: <code>{e}</code>",
            parse_mode="HTML", reply_markup=_close_kb(),
        )
        return

    if r["error"]:
        await message.answer(
            f"🔍 <b>Опрос выполнен</b>\nsince: <code>{since}</code>\n"
            f"ошибка: <code>{r.get('msg', 'unknown')}</code>",
            parse_mode="HTML", reply_markup=_close_kb(),
        )
        return

    count = len(r.get("data") or [])
    await message.answer(
        f"🔍 <b>Опрос выполнен</b>\n"
        f"since: <code>{since}</code>\n"
        f"найдено: <b>{count}</b>\n"
        f"ошибка: —",
        parse_mode="HTML", reply_markup=_close_kb(),
    )
