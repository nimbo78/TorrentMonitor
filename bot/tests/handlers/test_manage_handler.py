from bot.handlers.manage_handler import _topic_url, _item_caption


def test_topic_url_rutracker():
    item = {"tracker": "rutracker.org", "torrent_id": "12345"}
    assert _topic_url(item) == "https://rutracker.org/forum/viewtopic.php?t=12345"


def test_topic_url_kinozal():
    item = {"tracker": "kinozal.tv", "torrent_id": "777"}
    assert _topic_url(item) == "https://kinozal.tv/details.php?id=777"


def test_topic_url_rss_tracker_returns_none():
    # lostfilm — RSS-трекер, нет URL на раздачу
    item = {"tracker": "lostfilm.tv", "torrent_id": ""}
    assert _topic_url(item) is None


def test_topic_url_unknown_tracker_returns_none():
    item = {"tracker": "exotic-tracker.xyz", "torrent_id": "42"}
    assert _topic_url(item) is None


def test_topic_url_no_id_returns_none():
    item = {"tracker": "rutracker.org", "torrent_id": ""}
    assert _topic_url(item) is None


def test_caption_contains_clickable_link_for_known_tracker():
    item = {
        "name": "Ubuntu 24.04", "ep": "", "pause": 0,
        "tracker": "rutracker.org", "torrent_id": "12345",
        "timestamp": "2026-03-20 10:00:00",
    }
    caption = _item_caption(item)
    assert 'href="https://rutracker.org/forum/viewtopic.php?t=12345"' in caption
    assert "rutracker.org — раздача" in caption


def test_caption_no_link_for_rss_tracker():
    item = {
        "name": "Severance", "ep": "S04E04", "pause": 0,
        "tracker": "lostfilm.tv", "torrent_id": "",
        "timestamp": "2026-03-28 22:36:00",
    }
    caption = _item_caption(item)
    assert "href=" not in caption
    assert "lostfilm.tv" in caption
