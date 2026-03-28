from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.adapters.base import TMAdapter
from bot.config import Config

router = Router()


def _item_keyboard(item_id: int, paused: bool, sort: str, page: int) -> InlineKeyboardMarkup:
    action = "resume" if paused else "pause"
    label = "▶️ Возобновить" if paused else "⏸ Пауза"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=label, callback_data=f"do:{action}:{item_id}:{sort}:{page}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"do:confirm_del:{item_id}:{sort}:{page}"),
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"list:{sort}:{page}")],
    ])


def _confirm_del_keyboard(item_id: int, sort: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"do:delete:{item_id}:{sort}:{page}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"item:{item_id}:{sort}:{page}"),
        ],
    ])


@router.callback_query(F.data.startswith("item:"))
async def cb_item(call: CallbackQuery, adapter: TMAdapter, config: Config):
    _, item_id_str, sort, page_str = call.data.split(":")
    item_id = int(item_id_str)
    page = int(page_str)

    r = await adapter.list_torrents(sort_by=sort)
    if r["error"]:
        await call.answer(f"❌ {r['msg']}", show_alert=True)
        return

    item = next((i for i in (r["data"] or []) if i["id"] == item_id), None)
    if not item:
        await call.answer("Элемент не найден", show_alert=True)
        return

    ep = f" [{item['ep']}]" if item.get("ep") else ""
    state = "⏸ на паузе" if item.get("pause") else "▶️ активна"
    text = (
        f"<b>{item['name']}</b>{ep}\n"
        f"🔗 {item['tracker']}\n"
        f"📅 {str(item.get('timestamp', ''))[:16]}\n"
        f"Статус: {state}"
    )
    await call.message.edit_text(
        text,
        reply_markup=_item_keyboard(item_id, bool(item.get("pause")), sort, page),
        parse_mode="HTML",
    )
    await call.answer()


@router.callback_query(F.data.startswith("do:"))
async def cb_do(call: CallbackQuery, adapter: TMAdapter, config: Config):
    parts = call.data.split(":")
    action = parts[1]
    item_id = int(parts[2])
    sort = parts[3]
    page = int(parts[4])

    if action == "confirm_del":
        r = await adapter.list_torrents(sort_by=sort)
        item = next((i for i in (r.get("data") or []) if i["id"] == item_id), None)
        name = item["name"] if item else f"#{item_id}"
        await call.message.edit_text(
            f"⚠️ Удалить <b>{name}</b>?",
            reply_markup=_confirm_del_keyboard(item_id, sort, page),
            parse_mode="HTML",
        )
        await call.answer()
        return

    if action == "pause":
        r = await adapter.pause(item_id)
    elif action == "resume":
        r = await adapter.resume(item_id)
    elif action == "delete":
        r = await adapter.delete(item_id)
    else:
        await call.answer("Неизвестное действие", show_alert=True)
        return

    if r["error"]:
        await call.answer(f"❌ {r['msg']}", show_alert=True)
        return

    if action == "delete":
        await call.answer("🗑 Удалено")
        # Возвращаемся к списку
        from bot.handlers.list_handler import cb_list
        call.data = f"list:{sort}:{page}"
        await cb_list(call, adapter=adapter, config=config)
    else:
        await call.answer("✅ Готово")
        # Обновляем карточку элемента
        call.data = f"item:{item_id}:{sort}:{page}"
        await cb_item(call, adapter=adapter, config=config)
