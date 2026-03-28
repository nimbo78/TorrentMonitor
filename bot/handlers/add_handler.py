from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from bot.adapters.base import TMAdapter
from bot.config import Config

router = Router()


class AddStates(StatesGroup):
    waiting_url = State()
    waiting_serial_tracker = State()
    waiting_serial_name = State()


@router.message(Command("addurl"))
async def cmd_addurl(message: Message, state: FSMContext):
    await state.set_state(AddStates.waiting_url)
    await message.answer("Отправь URL темы с трекера:")


@router.message(AddStates.waiting_url)
async def process_url(message: Message, state: FSMContext, adapter: TMAdapter, config: Config):
    url = message.text.strip()
    await state.clear()
    r = await adapter.add_torrent(url)
    if r["error"]:
        await message.answer(f"❌ {r['msg']}")
    else:
        await message.answer(f"✅ {r['msg']}")


@router.message(Command("addserial"))
async def cmd_addserial(message: Message, state: FSMContext):
    await state.set_state(AddStates.waiting_serial_tracker)
    await message.answer("Укажи трекер (например: <code>lostfilm.tv</code>):", parse_mode="HTML")


@router.message(AddStates.waiting_serial_tracker)
async def process_serial_tracker(message: Message, state: FSMContext):
    await state.update_data(tracker=message.text.strip())
    await state.set_state(AddStates.waiting_serial_name)
    await message.answer("Теперь название сериала:")


@router.message(AddStates.waiting_serial_name)
async def process_serial_name(message: Message, state: FSMContext, adapter: TMAdapter, config: Config):
    data = await state.get_data()
    tracker = data["tracker"]
    name = message.text.strip()
    await state.clear()
    r = await adapter.add_serial(tracker, name)
    if r["error"]:
        await message.answer(f"❌ {r['msg']}")
    else:
        await message.answer(f"✅ {r['msg']}")
