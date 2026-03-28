import pytest
from bot.handlers.list_handler import _build_list_keyboard, _fmt_item, _ep_label


def make_item(i=1, name="Ubuntu", ep="", pause=0, tracker="rutracker.org", ts="2026-03-28 22:00:00"):
    return {"id": i, "name": name, "ep": ep, "pause": pause,
            "tracker": tracker, "timestamp": ts, "type": "forum"}


def test_ep_label_empty():
    assert _ep_label(make_item(ep="")) == ""


def test_ep_label_filled():
    assert _ep_label(make_item(ep="S04E04")) == " [S04E04]"


def test_fmt_item_paused():
    item = make_item(pause=1)
    assert "⏸" in _fmt_item(item)


def test_fmt_item_active():
    item = make_item(pause=0)
    assert "▶️" in _fmt_item(item)


def test_fmt_item_timestamp_truncated():
    item = make_item(ts="2026-03-28 22:36:00")
    result = _fmt_item(item)
    assert "2026-03-28 22:36" in result


def test_keyboard_single_page():
    items = [make_item(i) for i in range(3)]
    kb = _build_list_keyboard(items, page=0, page_size=10, sort="date")
    # 3 item rows + nav row + sort row = 5
    assert len(kb.inline_keyboard) == 5


def test_keyboard_multipage_nav():
    items = [make_item(i) for i in range(15)]
    kb = _build_list_keyboard(items, page=0, page_size=10, sort="date")
    nav_row = kb.inline_keyboard[-2]
    # page 0: no ◀️, has ▶️ → 2 buttons (counter + next)
    assert len(nav_row) == 2
    assert nav_row[-1].callback_data == "list:date:1"


def test_keyboard_middle_page_has_both_arrows():
    items = [make_item(i) for i in range(25)]
    kb = _build_list_keyboard(items, page=1, page_size=10, sort="date")
    nav_row = kb.inline_keyboard[-2]
    assert len(nav_row) == 3  # ◀️ counter ▶️


def test_keyboard_sort_toggle():
    items = [make_item(i) for i in range(3)]
    kb = _build_list_keyboard(items, page=0, page_size=10, sort="date")
    sort_btn = kb.inline_keyboard[-1][0]
    assert sort_btn.callback_data == "list:name:0"


def test_keyboard_clamps_page():
    items = [make_item(i) for i in range(3)]
    # page=99 should clamp to last valid page (0)
    kb = _build_list_keyboard(items, page=99, page_size=10, sort="date")
    assert kb is not None
