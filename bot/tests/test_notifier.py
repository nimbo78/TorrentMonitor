import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from bot.notifier import _notification_text, _fetch_tmdb_poster, _notify_item, _load_state, _save_state

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
        state = _load_state()
        assert state["last_seen"] == "2026-03-28 22:36:00"
    finally:
        notifier_mod.STATE_FILE = orig


def test_load_state_missing_file(tmp_path):
    import bot.notifier as notifier_mod
    orig = notifier_mod.STATE_FILE
    notifier_mod.STATE_FILE = tmp_path / "nonexistent.json"
    try:
        state = _load_state()
        assert state["last_seen"] == "2000-01-01 00:00:00"
    finally:
        notifier_mod.STATE_FILE = orig
