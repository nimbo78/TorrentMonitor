from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message

router = Router()


def close_button(text: str = "✖️ Закрыть") -> InlineKeyboardButton:
    """Стандартная кнопка удаления текущего сообщения."""
    return InlineKeyboardButton(text=text, callback_data="close")


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
