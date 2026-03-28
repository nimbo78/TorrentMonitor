from __future__ import annotations
import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
import httpx
from aiogram import Bot
from bot.adapters.base import TMAdapter
from bot.config import Config

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).parent / "data" / "state.json"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w300"


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_seen": "2000-01-01 00:00:00"}


def _save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state), encoding="utf-8")


async def _fetch_tmdb_poster(name: str, api_key: str) -> Optional[str]:
    """Ищет постер по названию в TMDB. Возвращает URL или None."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Пробуем как сериал, потом как фильм
            for media in ("tv", "movie"):
                resp = await client.get(
                    "https://api.themoviedb.org/3/search/" + media,
                    params={"api_key": api_key, "query": name, "language": "ru-RU"},
                )
                if resp.status_code != 200:
                    continue
                results = resp.json().get("results", [])
                if results and results[0].get("poster_path"):
                    return TMDB_IMAGE_BASE + results[0]["poster_path"]
    except Exception as e:
        logger.debug("TMDB lookup failed for %r: %s", name, e)
    return None


def _notification_text(item: dict) -> str:
    ep = f" [{item['ep']}]" if item.get("ep") else ""
    ts = str(item.get("timestamp", ""))[:16]
    return (
        f"🆕 <b>{item['name']}</b>{ep}\n"
        f"🔗 {item['tracker']}\n"
        f"📅 {ts}"
    )


async def _notify_item(bot: Bot, config: Config, item: dict) -> None:
    text = _notification_text(item)
    poster_url = None

    if config.tmdb_api_key:
        poster_url = await _fetch_tmdb_poster(item["name"], config.tmdb_api_key)

    for user_id in config.allowed_ids:
        try:
            if poster_url:
                await bot.send_photo(chat_id=user_id, photo=poster_url, caption=text, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
        except Exception as e:
            logger.warning("Failed to notify user %d: %s", user_id, e)


async def run_notifier(bot: Bot, adapter: TMAdapter, config: Config) -> None:
    """Infinite polling loop — runs as a background task alongside the dispatcher."""
    logger.info("Notifier started (interval=%ds)", config.poll_interval)
    state = _load_state()

    while True:
        try:
            r = await adapter.get_new_items(state["last_seen"])
            if not r["error"] and r["data"]:
                items = r["data"]
                logger.info("Found %d new item(s)", len(items))
                # Обновляем last_seen до отправки чтобы не дублировать при ошибке отправки
                new_last = max(i["timestamp"] for i in items)
                for item in items:
                    await _notify_item(bot, config, item)
                state["last_seen"] = new_last
                _save_state(state)
        except Exception as e:
            logger.error("Notifier error: %s", e)

        await asyncio.sleep(config.poll_interval)
