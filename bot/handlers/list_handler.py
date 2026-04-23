from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.adapters.base import TMAdapter
from bot.config import Config
from bot.handlers.common import close_button

router = Router()

_SORT_LABELS = {"date": "📅 по дате", "name": "🔤 по имени"}
_SORT_TOGGLE = {"date": "name", "name": "date"}


def _ep_label(item: dict) -> str:
    ep = item.get("ep", "")
    return f" [{ep}]" if ep else ""


def _fmt_item(item: dict) -> str:
    pause_icon = "⏸" if item.get("pause") else "▶️"
    ep = _ep_label(item)
    ts = str(item.get("timestamp", ""))[:16]  # "YYYY-MM-DD HH:MM"
    return f"{pause_icon} <b>{item['name']}</b>{ep}\n   <i>{item['tracker']} · {ts}</i>"


def _build_list_keyboard(
    items: list[dict],
    page: int,
    page_size: int,
    sort: str,
) -> InlineKeyboardMarkup:
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    chunk = items[page * page_size: (page + 1) * page_size]

    buttons: list[list[InlineKeyboardButton]] = []

    # Кнопка для каждого элемента
    for item in chunk:
        ep = _ep_label(item)
        label = f"{item['name']}{ep}"
        if len(label) > 40:
            label = label[:37] + "..."
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"item:{item['id']}:{sort}:{page}",
        )])

    # Навигация + сортировка
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"list:{sort}:{page - 1}"))
    nav.append(InlineKeyboardButton(
        text=f"{page + 1}/{total_pages}",
        callback_data="noop",
    ))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"list:{sort}:{page + 1}"))
    buttons.append(nav)

    # Переключение сортировки
    other_sort = _SORT_TOGGLE[sort]
    buttons.append([InlineKeyboardButton(
        text=f"Сортировать {_SORT_LABELS[other_sort]}",
        callback_data=f"list:{other_sort}:0",
    )])

    # Закрыть
    buttons.append([close_button()])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("list"))
async def cmd_list(message: Message, adapter: TMAdapter, config: Config):
    sort = "date"
    r = await adapter.list_torrents(sort_by=sort)
    if r["error"]:
        await message.answer(f"❌ {r['msg']}")
        return

    items = r["data"] or []
    if not items:
        await message.answer("Список пуст.")
        return

    page = 0
    text = f"📋 <b>Раздачи</b> ({len(items)}) — {_SORT_LABELS[sort]}\n\n"
    chunk = items[page * config.page_size: (page + 1) * config.page_size]
    text += "\n\n".join(_fmt_item(i) for i in chunk)

    await message.answer(
        text,
        reply_markup=_build_list_keyboard(items, page, config.page_size, sort),
        parse_mode="HTML",
    )


async def render_list(
    call: CallbackQuery,
    bot: Bot,
    adapter: TMAdapter,
    config: Config,
    sort: str,
    page: int,
) -> None:
    r = await adapter.list_torrents(sort_by=sort)
    if r["error"]:
        await call.answer(f"❌ {r['msg']}", show_alert=True)
        return

    items = r["data"] or []
    text = f"📋 <b>Раздачи</b> ({len(items)}) — {_SORT_LABELS[sort]}\n\n"
    chunk = items[page * config.page_size: (page + 1) * config.page_size]
    text += "\n\n".join(_fmt_item(i) for i in chunk)
    kb = _build_list_keyboard(items, page, config.page_size, sort)

    # Если предыдущее сообщение было фото (карточка с постером) —
    # edit_text не сработает, удаляем и шлём новое текстовое
    if call.message.photo:
        try:
            await call.message.delete()
        except Exception:
            pass
        await bot.send_message(
            chat_id=call.message.chat.id,
            text=text,
            reply_markup=kb,
            parse_mode="HTML",
        )
    else:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("list:"))
async def cb_list(call: CallbackQuery, bot: Bot, adapter: TMAdapter, config: Config):
    _, sort, page_str = call.data.split(":")
    await render_list(call, bot, adapter, config, sort, int(page_str))
    await call.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()
