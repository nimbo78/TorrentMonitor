from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.adapters.base import TMAdapter
from bot.config import Config
from bot.handlers.common import close_button

router = Router()


class CredStates(StatesGroup):
    waiting_login = State()
    waiting_password = State()
    waiting_passkey = State()


def _creds_keyboard(creds: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for c in creds:
        mark = "🔑" if c.get("log") else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{mark} {c['tracker']}",
            callback_data=f"cred:edit:{c['id']}",
        )])
    buttons.append([close_button()])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("credentials"))
async def cmd_credentials(message: Message, adapter: TMAdapter, config: Config):
    r = await adapter.get_credentials()
    if r["error"]:
        await message.answer(f"❌ {r['msg']}")
        return
    creds = r["data"] or []
    if not creds:
        await message.answer("Учётных данных нет.")
        return
    await message.answer(
        "🔐 <b>Трекеры</b> — нажми для редактирования:",
        reply_markup=_creds_keyboard(creds),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("cred:edit:"))
async def cb_cred_edit(call: CallbackQuery, state: FSMContext):
    cred_id = int(call.data.split(":")[2])
    await state.update_data(cred_id=cred_id)
    await state.set_state(CredStates.waiting_login)
    await call.message.answer("Введи логин (или «-» чтобы оставить пустым, /cancel — отмена):")
    await call.answer()


@router.message(CredStates.waiting_login)
async def process_login(message: Message, state: FSMContext):
    val = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(login=val)
    await state.set_state(CredStates.waiting_password)
    await message.answer("Введи пароль (или «-» чтобы оставить пустым, /cancel — отмена):")


@router.message(CredStates.waiting_password)
async def process_password(message: Message, state: FSMContext):
    val = "" if message.text.strip() == "-" else message.text.strip()
    await state.update_data(password=val)
    await state.set_state(CredStates.waiting_passkey)
    await message.answer("Введи passkey (или «-» чтобы пропустить, /cancel — отмена):")


@router.message(CredStates.waiting_passkey)
async def process_passkey(message: Message, state: FSMContext, adapter: TMAdapter, config: Config):
    val = "" if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()
    await state.clear()
    r = await adapter.set_credentials(
        data["cred_id"], data["login"], data["password"], val
    )
    if r["error"]:
        await message.answer(f"❌ {r['msg']}")
    else:
        await message.answer("✅ Учётные данные сохранены.")
