from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from bot.adapters.base import TMAdapter
from bot.config import Config

router = Router()


@router.message(Command("errors"))
async def cmd_errors(message: Message, adapter: TMAdapter, config: Config):
    r = await adapter.get_warnings()
    if r["error"]:
        await message.answer(f"❌ {r['msg']}")
        return

    warnings = r["data"] or []
    if not warnings:
        await message.answer("✅ Ошибок нет.")
        return

    lines = [f"⚠️ <b>Ошибки</b> ({len(warnings)})\n"]
    for w in warnings[:20]:  # первые 20
        ts = str(w.get("time", ""))[:16]
        location = w.get("location") or w.get("where", "?")
        reason = w.get("reason", "")
        lines.append(f"• <b>{location}</b> — {reason}\n  <i>{ts}</i>")

    if len(warnings) > 20:
        lines.append(f"\n…и ещё {len(warnings) - 20}")

    await message.answer("\n".join(lines), parse_mode="HTML")
