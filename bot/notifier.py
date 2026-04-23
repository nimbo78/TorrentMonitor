from __future__ import annotations
import asyncio
import json
import logging
import time
from datetime import datetime
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

# Состояние нотификатора для /status команды
_HEALTH: dict = {
    "last_poll_at": None,   # str — время последнего опроса
    "last_poll_ok": None,   # bool — был ли последний опрос успешен
    "last_error": None,     # str | None — текст последней ошибки
    "last_count": 0,        # int — сколько найдено в последний раз
    "last_seen": None,      # str — актуальный last_seen
}


def _now_ts() -> str:
    """Текущее время в формате TM timestamp."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_health() -> dict:
    """Публичный геттер для /status handler."""
    return dict(_HEALTH)


def read_last_seen() -> str:
    """Публичный геттер для /poll handler."""
    state, _ = _load_state()
    return state["last_seen"]


def _load_state() -> tuple[dict, bool]:
    """Возвращает (state, is_first_run).

    При отсутствии/повреждении файла bootstrap-им last_seen в текущее время,
    чтобы не флудить историческими раздачами на первом запуске.
    """
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8")), False
        except Exception:
            pass
    return {"last_seen": _now_ts()}, True


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


async def _notifier_tick(
    bot: Bot, adapter: TMAdapter, config: Config, state: dict
) -> dict:
    """Одна итерация опроса. Обновляет state и _HEALTH, возвращает обновлённый state."""
    since = state["last_seen"]
    _HEALTH["last_poll_at"] = _now_ts()
    _HEALTH["last_seen"] = since

    logger.info("Polling since %s", since)
    try:
        r = await adapter.get_new_items(since)
    except Exception as e:
        logger.error("Notifier exception: %s", e)
        _HEALTH["last_poll_ok"] = False
        _HEALTH["last_error"] = str(e)
        return state

    if r["error"]:
        msg = r.get("msg") or "unknown error"
        logger.warning("TM API error: %s", msg)
        _HEALTH["last_poll_ok"] = False
        _HEALTH["last_error"] = msg
        return state

    items = r.get("data") or []
    _HEALTH["last_poll_ok"] = True
    _HEALTH["last_error"] = None
    _HEALTH["last_count"] = len(items)

    if not items:
        logger.info("No new items since %s", since)
        return state

    # Обновляем last_seen до отправки, чтобы не дублировать при ошибке отправки
    new_last = max(i["timestamp"] for i in items)
    for item in items:
        await _notify_item(bot, config, item)
    state["last_seen"] = new_last
    _save_state(state)
    _HEALTH["last_seen"] = new_last
    logger.info("Found %d new item(s), new last_seen=%s", len(items), new_last)
    return state


async def run_notifier(bot: Bot, adapter: TMAdapter, config: Config) -> None:
    """Infinite polling loop — runs as a background task alongside the dispatcher."""
    _load_poster_cache()
    state, is_first_run = _load_state()
    logger.info(
        "Notifier started (interval=%ds, last_seen=%s, first_run=%s)",
        config.poll_interval, state["last_seen"], is_first_run,
    )
    if is_first_run:
        # Сохраняем bootstrap-нутый last_seen сразу, чтобы падение до первого опроса
        # не приводило к повторной инициализации на "2000-01-01".
        _save_state(state)
    _HEALTH["last_seen"] = state["last_seen"]

    while True:
        state = await _notifier_tick(bot, adapter, config, state)
        await asyncio.sleep(config.poll_interval)
