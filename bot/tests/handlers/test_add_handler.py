import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.handlers.add_handler import (
    _tracker_keyboard, _quality_keyboard, _quality_options_for,
    cmd_addserial, cb_pick_tracker, cb_pick_quality, process_serial_name,
    AddStates,
)
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


def test_quality_options_default_mapping():
    """Для обычных RSS-трекеров: SD=0, HD 720=1, FHD 1080=2."""
    opts = _quality_options_for("baibako.tv")
    assert opts == [("SD", 0), ("HD 720", 1), ("FHD 1080", 2)]
    # для остальных трекеров тоже default
    assert _quality_options_for("newstudio.tv") == opts
    assert _quality_options_for("hamsterstudio.org") == opts
    # неизвестный трекер тоже получает default
    assert _quality_options_for("unknown.tv") == opts


def test_quality_options_lostfilm_mapping():
    """Для lostfilm.tv и lostfilm-mirror HD/FHD коды инвертированы."""
    expected = [("SD", 0), ("HD 720 MP4", 2), ("FHD 1080", 1)]
    assert _quality_options_for("lostfilm.tv") == expected
    assert _quality_options_for("lostfilm-mirror") == expected


def test_quality_keyboard_default():
    kb = _quality_keyboard("baibako.tv")
    assert len(kb.inline_keyboard) == 2
    assert len(kb.inline_keyboard[0]) == 3
    assert kb.inline_keyboard[0][0].callback_data == "addserial:quality:0"  # SD
    assert kb.inline_keyboard[0][1].callback_data == "addserial:quality:1"  # HD 720
    assert kb.inline_keyboard[0][2].callback_data == "addserial:quality:2"  # FHD 1080
    assert kb.inline_keyboard[1][0].callback_data == "close"


def test_quality_keyboard_lostfilm_has_swapped_values():
    """Для lostfilm кнопки HD/FHD имеют инвертированные callback_data."""
    kb = _quality_keyboard("lostfilm-mirror")
    assert kb.inline_keyboard[0][0].callback_data == "addserial:quality:0"  # SD
    assert kb.inline_keyboard[0][1].callback_data == "addserial:quality:2"  # HD 720 MP4
    assert kb.inline_keyboard[0][2].callback_data == "addserial:quality:1"  # FHD 1080


@pytest.mark.asyncio
async def test_process_serial_name_advances_to_quality_lostfilm():
    """После ввода имени для lostfilm — клавиатура с lostfilm-маппингом."""
    msg = MagicMock()
    msg.text = "Severance"
    msg.answer = AsyncMock()
    state = MagicMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.get_data = AsyncMock(return_value={"tracker": "lostfilm-mirror"})

    await process_serial_name(msg, state)

    state.update_data.assert_awaited_once_with(name="Severance")
    state.set_state.assert_awaited_once_with(AddStates.waiting_serial_quality)
    args = msg.answer.await_args
    kb = args.kwargs["reply_markup"]
    # для lostfilm-mirror FHD 1080 → hd=1, HD 720 MP4 → hd=2
    assert kb.inline_keyboard[0][1].callback_data == "addserial:quality:2"
    assert kb.inline_keyboard[0][2].callback_data == "addserial:quality:1"


@pytest.mark.asyncio
async def test_process_serial_name_default_tracker_uses_default_mapping():
    msg = MagicMock()
    msg.text = "Severance"
    msg.answer = AsyncMock()
    state = MagicMock()
    state.update_data = AsyncMock()
    state.set_state = AsyncMock()
    state.get_data = AsyncMock(return_value={"tracker": "baibako.tv"})

    await process_serial_name(msg, state)

    args = msg.answer.await_args
    kb = args.kwargs["reply_markup"]
    assert kb.inline_keyboard[0][1].callback_data == "addserial:quality:1"
    assert kb.inline_keyboard[0][2].callback_data == "addserial:quality:2"


@pytest.mark.asyncio
async def test_cb_pick_quality_calls_add_serial_with_hd():
    call = MagicMock()
    call.data = "addserial:quality:2"  # FHD 1080
    call.message = MagicMock()
    call.message.delete = AsyncMock()
    call.message.answer = AsyncMock()
    call.answer = AsyncMock()

    state = MagicMock()
    state.get_data = AsyncMock(return_value={"tracker": "lostfilm.tv", "name": "Severance"})
    state.clear = AsyncMock()

    adapter = MagicMock()
    adapter.add_serial = AsyncMock(return_value=ok(None, "Сериал добавлен."))

    await cb_pick_quality(call, state, adapter, _make_cfg())

    adapter.add_serial.assert_awaited_once_with("lostfilm.tv", "Severance", 2)
    state.clear.assert_awaited_once()


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
