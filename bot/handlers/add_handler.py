from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.adapters.base import TMAdapter
from bot.config import Config
from bot.handlers.common import close_button

router = Router()


class AddStates(StatesGroup):
    waiting_url = State()
    waiting_serial_name = State()
    waiting_serial_quality = State()


# Качество в том же порядке что и в веб-UI TorrentMonitor
_QUALITY_OPTIONS: list[tuple[int, str]] = [
    (0, "SD"),
    (1, "HD 720 MP4"),
    (2, "FHD 1080"),
]


def _quality_keyboard() -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(text=label, callback_data=f"addserial:quality:{hd}")
        for hd, label in _QUALITY_OPTIONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=[row, [close_button()]])


# ───────── /addurl ─────────

@router.message(Command("addurl"))
async def cmd_addurl(message: Message, state: FSMContext):
    await state.set_state(AddStates.waiting_url)
    await message.answer("Отправь URL темы с трекера (/cancel — отмена):")


@router.message(AddStates.waiting_url)
async def process_url(message: Message, state: FSMContext, adapter: TMAdapter, config: Config):
    url = message.text.strip()
    await state.clear()
    r = await adapter.add_torrent(url)
    if r["error"]:
        await message.answer(f"❌ {r['msg']}")
    else:
        await message.answer(f"✅ {r['msg']}")


# ───────── /addserial ─────────

# RSS-трекеры (для сериалов). Используется как фолбэк, если api.php не
# возвращает поле type (совместимость с alfonder-образом).
_KNOWN_RSS_TRACKERS = {
    "lostfilm.tv", "lostfilm-mirror", "baibako.tv", "newstudio.tv",
    "hamsterstudio.org",
}


def _is_rss(cred: dict) -> bool:
    t = cred.get("type")
    if t:
        return t == "RSS"
    return cred.get("tracker") in _KNOWN_RSS_TRACKERS


def _tracker_keyboard(trackers: list[str]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=f"📺 {t}", callback_data=f"addserial:tracker:{t}")]
        for t in trackers
    ]
    buttons.append([close_button()])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("addserial"))
async def cmd_addserial(message: Message, adapter: TMAdapter, config: Config):
    r = await adapter.get_credentials()
    if r["error"]:
        await message.answer(f"❌ {r['msg']}")
        return

    creds = r["data"] or []
    # Сериалы добавляются на RSS-трекерах. Форумные — через /addurl.
    # Берём только трекеры с настроенным логином — иначе TM всё равно откажется.
    rss_trackers = sorted({
        c["tracker"] for c in creds
        if _is_rss(c) and c.get("log")
    })

    if not rss_trackers:
        await message.answer(
            "Нет RSS-трекеров с настроенными учётками.\n"
            "Настрой их через /credentials."
        )
        return

    await message.answer(
        "Выбери трекер для добавления сериала:",
        reply_markup=_tracker_keyboard(rss_trackers),
    )


@router.callback_query(F.data.startswith("addserial:tracker:"))
async def cb_pick_tracker(call: CallbackQuery, state: FSMContext):
    tracker = call.data.split(":", 2)[2]
    await state.update_data(tracker=tracker)
    await state.set_state(AddStates.waiting_serial_name)
    try:
        await call.message.delete()
    except Exception:
        pass
    await call.message.answer(
        f"Трекер: <b>{tracker}</b>\nТеперь название сериала (/cancel — отмена):",
        parse_mode="HTML",
    )
    await call.answer()


@router.message(AddStates.waiting_serial_name)
async def process_serial_name(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(AddStates.waiting_serial_quality)
    await message.answer(
        f"Название: <b>{name}</b>\nВыбери качество:",
        parse_mode="HTML",
        reply_markup=_quality_keyboard(),
    )


@router.callback_query(F.data.startswith("addserial:quality:"))
async def cb_pick_quality(
    call: CallbackQuery, state: FSMContext, adapter: TMAdapter, config: Config
):
    hd = int(call.data.split(":", 2)[2])
    data = await state.get_data()
    tracker = data.get("tracker", "")
    name = data.get("name", "")
    await state.clear()

    try:
        await call.message.delete()
    except Exception:
        pass

    r = await adapter.add_serial(tracker, name, hd)
    if r["error"]:
        await call.message.answer(f"❌ {r['msg']}")
    else:
        await call.message.answer(f"✅ {r['msg']}")
    await call.answer()
