from __future__ import annotations
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional
import httpx
from aiogram import Bot
from bot.adapters.base import TMAdapter
from bot.config import Config

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).parent / "data" / "state.json"
POSTER_CACHE_FILE = Path(__file__).parent / "data" / "poster_cache.json"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w300"

# In-memory кэш: name → (url|None, timestamp)
_POSTER_CACHE: dict[str, tuple[Optional[str], float]] = {}
_POSTER_TTL_HIT = 7 * 24 * 3600   # 7 дней для найденных постеров
_POSTER_TTL_MISS = 24 * 3600      # 1 день для промахов — вдруг добавят в TMDB


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


def _load_poster_cache() -> None:
    """Поднимает кэш с диска при старте бота."""
    global _POSTER_CACHE
    if POSTER_CACHE_FILE.exists():
        try:
            raw = json.loads(POSTER_CACHE_FILE.read_text(encoding="utf-8"))
            _POSTER_CACHE = {k: tuple(v) for k, v in raw.items()}
        except Exception:
            _POSTER_CACHE = {}


def _save_poster_cache() -> None:
    POSTER_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        POSTER_CACHE_FILE.write_text(
            json.dumps({k: list(v) for k, v in _POSTER_CACHE.items()}),
            encoding="utf-8",
        )
    except Exception as e:
        logger.debug("Failed to save poster cache: %s", e)


async def _fetch_tmdb_poster(name: str, api_key: str) -> Optional[str]:
    """Ищет постер по названию в TMDB. Кэширует результат (включая промахи)."""
    now = time.time()
    cached = _POSTER_CACHE.get(name)
    if cached:
        url, ts = cached
        ttl = _POSTER_TTL_HIT if url else _POSTER_TTL_MISS
        if now - ts < ttl:
            return url

    result: Optional[str] = None
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
                    result = TMDB_IMAGE_BASE + results[0]["poster_path"]
                    break
    except Exception as e:
        logger.debug("TMDB lookup failed for %r: %s", name, e)

    _POSTER_CACHE[name] = (result, now)
    _save_poster_cache()
    return result


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
    _load_poster_cache()
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
