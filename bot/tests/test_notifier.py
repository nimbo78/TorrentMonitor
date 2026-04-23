import pytest
import json
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from bot.notifier import (
    _notification_text, _fetch_tmdb_poster, _notify_item,
    _load_state, _save_state, _notifier_tick,
)
from bot.adapters.base import ok, err

def make_item(name="Severance", ep="S04E04", ts="2026-03-28 22:36:00", tracker="lostfilm.tv"):
    return {"id": 2, "name": name, "ep": ep, "timestamp": ts, "tracker": tracker, "pause": 0}


def make_cfg(tmdb_key=""):
    from bot.config import Config
    return Config.load(env={
        "TELEGRAM_BOT_TOKEN": "tok",
        "TELEGRAM_ALLOWED_IDS": "111,222",
        "TMDB_API_KEY": tmdb_key,
    })


def test_notification_text_with_ep():
    item = make_item()
    text = _notification_text(item)
    assert "Severance" in text
    assert "[S04E04]" in text
    assert "lostfilm.tv" in text
    assert "2026-03-28 22:36" in text


def test_notification_text_no_ep():
    item = make_item(ep="")
    text = _notification_text(item)
    assert "[" not in text


@pytest.mark.asyncio
async def test_notify_item_no_tmdb(tmp_path):
    cfg = make_cfg(tmdb_key="")
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()

    await _notify_item(bot, cfg, make_item())

    assert bot.send_message.call_count == 2  # 2 allowed_ids
    bot.send_photo.assert_not_called()


@pytest.mark.asyncio
async def test_notify_item_with_poster(tmp_path):
    cfg = make_cfg(tmdb_key="testkey")
    bot = MagicMock()
    bot.send_photo = AsyncMock()
    bot.send_message = AsyncMock()

    with patch("bot.notifier._fetch_tmdb_poster", new=AsyncMock(return_value="https://img/poster.jpg")):
        await _notify_item(bot, cfg, make_item())

    assert bot.send_photo.call_count == 2
    bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_notify_item_poster_fallback_on_none(tmp_path):
    cfg = make_cfg(tmdb_key="testkey")
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()

    with patch("bot.notifier._fetch_tmdb_poster", new=AsyncMock(return_value=None)):
        await _notify_item(bot, cfg, make_item())

    assert bot.send_message.call_count == 2
    bot.send_photo.assert_not_called()


def test_state_roundtrip(tmp_path):
    import bot.notifier as notifier_mod
    orig = notifier_mod.STATE_FILE
    notifier_mod.STATE_FILE = tmp_path / "state.json"
    try:
        _save_state({"last_seen": "2026-03-28 22:36:00"})
        state, is_first_run = _load_state()
        assert state["last_seen"] == "2026-03-28 22:36:00"
        assert is_first_run is False
    finally:
        notifier_mod.STATE_FILE = orig


def test_load_state_first_run_bootstraps_to_now(tmp_path, monkeypatch):
    """Первый запуск должен дать last_seen = now(), а не 2000 год."""
    import bot.notifier as notifier_mod
    orig = notifier_mod.STATE_FILE
    notifier_mod.STATE_FILE = tmp_path / "nonexistent.json"
    monkeypatch.setattr(notifier_mod, "_now_ts", lambda: "2026-04-24 12:00:00")
    try:
        state, is_first_run = _load_state()
        assert state["last_seen"] == "2026-04-24 12:00:00"
        assert is_first_run is True
    finally:
        notifier_mod.STATE_FILE = orig


def test_load_state_existing_preserves_value(tmp_path):
    import bot.notifier as notifier_mod
    orig = notifier_mod.STATE_FILE
    notifier_mod.STATE_FILE = tmp_path / "state.json"
    try:
        _save_state({"last_seen": "2020-01-01 00:00:00"})
        state, is_first_run = _load_state()
        assert state["last_seen"] == "2020-01-01 00:00:00"
        assert is_first_run is False
    finally:
        notifier_mod.STATE_FILE = orig


@pytest.mark.asyncio
async def test_poster_cache_hit(tmp_path, monkeypatch):
    """Повторный запрос того же имени не должен ходить в TMDB."""
    import bot.notifier as notifier_mod
    notifier_mod.POSTER_CACHE_FILE = tmp_path / "poster_cache.json"
    notifier_mod._POSTER_CACHE.clear()

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": [{"poster_path": "/x.jpg"}]}
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("bot.notifier.httpx.AsyncClient", return_value=mock_client):
        url1 = await _fetch_tmdb_poster("Severance", "key")
        url2 = await _fetch_tmdb_poster("Severance", "key")

    assert url1 == url2
    assert url1.endswith("/x.jpg")
    # второй вызов не должен делать HTTP-запрос
    assert mock_client.get.call_count == 1


@pytest.mark.asyncio
async def test_poster_cache_miss_also_cached(tmp_path, monkeypatch):
    """Промахи тоже кэшируются чтобы не долбить TMDB."""
    import bot.notifier as notifier_mod
    notifier_mod.POSTER_CACHE_FILE = tmp_path / "poster_cache.json"
    notifier_mod._POSTER_CACHE.clear()

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": []}
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("bot.notifier.httpx.AsyncClient", return_value=mock_client):
        r1 = await _fetch_tmdb_poster("NotReal", "key")
        r2 = await _fetch_tmdb_poster("NotReal", "key")

    assert r1 is None
    assert r2 is None
    # первый вызов делает 2 запроса (tv + movie), второй — 0 (из кэша)
    assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_notifier_tick_logs_api_error(tmp_path, caplog):
    import bot.notifier as notifier_mod
    notifier_mod.STATE_FILE = tmp_path / "state.json"
    notifier_mod._HEALTH.update({"last_poll_ok": None, "last_error": None})

    adapter = MagicMock()
    adapter.get_new_items = AsyncMock(return_value=err("boom"))
    cfg = make_cfg()
    bot = MagicMock()
    state = {"last_seen": "2026-04-24 00:00:00"}

    with caplog.at_level(logging.WARNING, logger="bot.notifier"):
        await _notifier_tick(bot, adapter, cfg, state)

    assert any("TM API error: boom" in m for m in caplog.messages)
    assert notifier_mod._HEALTH["last_poll_ok"] is False
    assert notifier_mod._HEALTH["last_error"] == "boom"


@pytest.mark.asyncio
async def test_notifier_tick_empty_logs_since(tmp_path, caplog):
    import bot.notifier as notifier_mod
    notifier_mod.STATE_FILE = tmp_path / "state.json"

    adapter = MagicMock()
    adapter.get_new_items = AsyncMock(return_value=ok([]))
    cfg = make_cfg()
    bot = MagicMock()
    state = {"last_seen": "2026-04-24 00:00:00"}

    with caplog.at_level(logging.INFO, logger="bot.notifier"):
        new_state = await _notifier_tick(bot, adapter, cfg, state)

    assert new_state["last_seen"] == "2026-04-24 00:00:00"  # не изменился
    assert any("No new items since 2026-04-24 00:00:00" in m for m in caplog.messages)
    assert notifier_mod._HEALTH["last_count"] == 0


@pytest.mark.asyncio
async def test_notifier_tick_new_items_updates_state_and_health(tmp_path):
    import bot.notifier as notifier_mod
    notifier_mod.STATE_FILE = tmp_path / "state.json"

    items = [
        make_item(name="Severance", ts="2026-04-24 22:36:00"),
        make_item(name="Ubuntu", ts="2026-04-24 10:00:00"),
    ]
    adapter = MagicMock()
    adapter.get_new_items = AsyncMock(return_value=ok(items))
    cfg = make_cfg(tmdb_key="")  # без TMDB → send_message
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()
    state = {"last_seen": "2026-04-23 00:00:00"}

    new_state = await _notifier_tick(bot, adapter, cfg, state)

    assert new_state["last_seen"] == "2026-04-24 22:36:00"  # max из items
    assert notifier_mod._HEALTH["last_count"] == 2
    assert notifier_mod._HEALTH["last_poll_ok"] is True
    # state.json записан на диск
    saved = json.loads((tmp_path / "state.json").read_text())
    assert saved["last_seen"] == "2026-04-24 22:36:00"


def test_poster_cache_roundtrip(tmp_path):
    """Кэш переживает рестарт — save на диск, load с диска."""
    import bot.notifier as notifier_mod
    notifier_mod.POSTER_CACHE_FILE = tmp_path / "poster_cache.json"
    notifier_mod._POSTER_CACHE.clear()
    notifier_mod._POSTER_CACHE["Severance"] = ("https://img/poster.jpg", 1700000000.0)

    notifier_mod._save_poster_cache()

    # имитируем рестарт бота
    notifier_mod._POSTER_CACHE.clear()
    notifier_mod._load_poster_cache()

    assert notifier_mod._POSTER_CACHE["Severance"] == ("https://img/poster.jpg", 1700000000.0)
