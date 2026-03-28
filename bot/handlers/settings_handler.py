from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.adapters.base import TMAdapter
from bot.config import Config

router = Router()

# Ключи настроек доступных для редактирования через бота
_EDITABLE_KEYS = [
    "proxy", "proxyAddress", "proxyType",
    "savePath", "torrentClientHost", "torrentClientPort",
]


class SettingsStates(StatesGroup):
    waiting_value = State()


def _settings_keyboard(settings: dict) -> InlineKeyboardMarkup:
    buttons = []
    for key in _EDITABLE_KEYS:
        val = settings.get(key, "—")
        if len(str(val)) > 20:
            val = str(val)[:17] + "..."
        buttons.append([InlineKeyboardButton(
            text=f"{key}: {val}",
            callback_data=f"setting:edit:{key}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("settings"))
async def cmd_settings(message: Message, adapter: TMAdapter, config: Config):
    r = await adapter.get_settings()
    if r["error"]:
        await message.answer(f"❌ {r['msg']}")
        return
    settings = r["data"] or {}
    await message.answer(
        "⚙️ <b>Настройки</b> — нажми для изменения:",
        reply_markup=_settings_keyboard(settings),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("setting:edit:"))
async def cb_setting_edit(call: CallbackQuery, state: FSMContext):
    key = call.data.split(":")[2]
    await state.update_data(key=key)
    await state.set_state(SettingsStates.waiting_value)
    await call.message.answer(f"Новое значение для <code>{key}</code>:", parse_mode="HTML")
    await call.answer()


@router.message(SettingsStates.waiting_value)
async def process_setting_value(message: Message, state: FSMContext, adapter: TMAdapter, config: Config):
    data = await state.get_data()
    key = data["key"]
    value = message.text.strip()
    await state.clear()
    r = await adapter.update_setting(key, value)
    if r["error"]:
        await message.answer(f"❌ {r['msg']}")
    else:
        await message.answer(f"✅ <code>{key}</code> = <code>{value}</code>", parse_mode="HTML")
