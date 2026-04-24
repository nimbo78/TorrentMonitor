import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.handlers.add_handler import _tracker_keyboard, cmd_addserial, cb_pick_tracker, AddStates
from bot.adapters.base import ok, err

def _make_cfg():
    from bot.config import Config
    return Config.load(env={
        "TELEGRAM_BOT_TOKEN": "tok",
        "TELEGRAM_ALLOWED_IDS": "1",
    })


def test_tracker_keyboard_has_buttons_and_close():
    kb = _tracker_keyboard(["lostfilm.tv", "baibako.tv"])
    # 2 трекера + строка "Закрыть"
    assert len(kb.inline_keyboard) == 3
    assert kb.inline_keyboard[0][0].callback_data == "addserial:tracker:lostfilm.tv"
    assert kb.inline_keyboard[1][0].callback_data == "addserial:tracker:baibako.tv"
    assert kb.inline_keyboard[-1][0].callback_data == "close"


@pytest.mark.asyncio
async def test_addserial_empty_list_no_state(tmp_path):
    adapter = MagicMock()
    adapter.get_credentials = AsyncMock(return_value=ok([]))
    msg = MagicMock()
    msg.answer = AsyncMock()
    state = MagicMock()
    state.set_state = AsyncMock()

    await cmd_addserial(msg, adapter, _make_cfg())

    msg.answer.assert_awaited_once()
    args = msg.answer.await_args
    assert "Нет RSS-трекеров" in args.args[0]
    # state не трогаем — чтобы не застрять в waiting_serial_name
    state.set_state.assert_not_called()


@pytest.mark.asyncio
async def test_addserial_filters_rss_only_using_type():
    adapter = MagicMock()
    adapter.get_credentials = AsyncMock(return_value=ok([
        {"id": 1, "tracker": "rutracker.org", "log": "u", "type": "forum", "necessarily": 1},
        {"id": 2, "tracker": "lostfilm.tv",   "log": "u", "type": "RSS",   "necessarily": 1},
        {"id": 3, "tracker": "baibako.tv",    "log": "u", "type": "RSS",   "necessarily": 1},
        {"id": 4, "tracker": "nnmclub.to",    "log": "u", "type": "forum", "necessarily": 1},
    ]))
    captured_kb = {}
    msg = MagicMock()
    async def _answer(text, reply_markup=None, **kw):
        captured_kb["kb"] = reply_markup
    msg.answer = AsyncMock(side_effect=_answer)

    await cmd_addserial(msg, adapter, _make_cfg())

    kb = captured_kb["kb"]
    callback_datas = [row[0].callback_data for row in kb.inline_keyboard if row[0].callback_data != "close"]
    assert callback_datas == ["addserial:tracker:baibako.tv", "addserial:tracker:lostfilm.tv"]


@pytest.mark.asyncio
async def test_addserial_falls_back_to_known_rss_list_when_no_type():
    """Если api.php не вернул type (старый alfonder образ) — используем whitelist."""
    adapter = MagicMock()
    adapter.get_credentials = AsyncMock(return_value=ok([
        {"id": 1, "tracker": "rutracker.org",    "log": "u", "necessarily": 1},
        {"id": 2, "tracker": "lostfilm.tv",      "log": "u", "necessarily": 1},
        {"id": 3, "tracker": "lostfilm-mirror",  "log": "u", "necessarily": 1},
        {"id": 4, "tracker": "hamsterstudio.org", "log": "",  "necessarily": 1},  # без логина
        {"id": 5, "tracker": "nnmclub.to",       "log": "u", "necessarily": 1},
    ]))
    captured_kb = {}
    msg = MagicMock()
    async def _answer(text, reply_markup=None, **kw):
        captured_kb["kb"] = reply_markup
    msg.answer = AsyncMock(side_effect=_answer)

    await cmd_addserial(msg, adapter, _make_cfg())

    kb = captured_kb["kb"]
    callback_datas = [row[0].callback_data for row in kb.inline_keyboard if row[0].callback_data != "close"]
    # только известные RSS + с заполненным log
    assert callback_datas == [
        "addserial:tracker:lostfilm-mirror",
        "addserial:tracker:lostfilm.tv",
    ]


@pytest.mark.asyncio
async def test_cb_pick_tracker_sets_state_and_tracker():
    call = MagicMock()
    call.data = "addserial:tracker:lostfilm.tv"
    call.message = MagicMock()
    call.message.delete = AsyncMock()
    call.message.answer = AsyncMock()
    call.answer = AsyncMock()

    state = MagicMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()

    await cb_pick_tracker(call, state)

    state.update_data.assert_awaited_once_with(tracker="lostfilm.tv")
    state.set_state.assert_awaited_once_with(AddStates.waiting_serial_name)
    call.message.answer.assert_awaited_once()
    prompt = call.message.answer.await_args.args[0]
    assert "lostfilm.tv" in prompt
    assert "/cancel" in prompt
