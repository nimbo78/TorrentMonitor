import pytest
from bot.tests.conftest import make_db_config
from bot.adapters.db_adapter import DBAdapter

pytestmark = pytest.mark.asyncio


async def test_list_all(sqlite_db):
    adapter = DBAdapter(make_db_config(sqlite_db))
    r = await adapter.list_torrents()
    assert r["error"] is False
    assert len(r["data"]) == 2


async def test_list_sort_by_name(sqlite_db):
    adapter = DBAdapter(make_db_config(sqlite_db))
    r = await adapter.list_torrents(sort_by="name")
    names = [i["name"] for i in r["data"]]
    assert names == sorted(names)


async def test_list_sort_by_date(sqlite_db):
    adapter = DBAdapter(make_db_config(sqlite_db))
    r = await adapter.list_torrents(sort_by="date")
    ts = [i["timestamp"] for i in r["data"]]
    assert ts == sorted(ts, reverse=True)


async def test_item_has_type(sqlite_db):
    adapter = DBAdapter(make_db_config(sqlite_db))
    r = await adapter.list_torrents()
    by_tracker = {i["tracker"]: i for i in r["data"]}
    assert by_tracker["rutracker.org"]["type"] == "forum"
    assert by_tracker["lostfilm.tv"]["type"] == "RSS"


async def test_pause_resume(sqlite_db):
    adapter = DBAdapter(make_db_config(sqlite_db))
    await adapter.pause(1)
    items = (await adapter.list_torrents())["data"]
    assert next(i for i in items if i["id"] == 1)["pause"] == 1
    await adapter.resume(1)
    items = (await adapter.list_torrents())["data"]
    assert next(i for i in items if i["id"] == 1)["pause"] == 0


async def test_delete(sqlite_db):
    adapter = DBAdapter(make_db_config(sqlite_db))
    await adapter.delete(1)
    items = (await adapter.list_torrents())["data"]
    assert all(i["id"] != 1 for i in items)


async def test_get_warnings(sqlite_db):
    adapter = DBAdapter(make_db_config(sqlite_db))
    r = await adapter.get_warnings()
    assert r["error"] is False
    assert r["data"][0]["reason"] == "cookie_expired"


async def test_get_credentials_no_passwords(sqlite_db):
    adapter = DBAdapter(make_db_config(sqlite_db))
    r = await adapter.get_credentials()
    assert r["error"] is False
    for cred in r["data"]:
        assert "pass" not in cred
        assert "cookie" not in cred


async def test_get_settings(sqlite_db):
    adapter = DBAdapter(make_db_config(sqlite_db))
    r = await adapter.get_settings()
    assert r["error"] is False
    assert r["data"]["proxy"] == "0"


async def test_update_setting(sqlite_db):
    adapter = DBAdapter(make_db_config(sqlite_db))
    r = await adapter.update_setting("proxy", "1")
    assert r["error"] is False
    r2 = await adapter.get_settings()
    assert r2["data"]["proxy"] == "1"


async def test_get_new_items(sqlite_db):
    adapter = DBAdapter(make_db_config(sqlite_db))
    r = await adapter.get_new_items("2026-03-25 00:00:00")
    assert r["error"] is False
    assert len(r["data"]) == 1
    assert r["data"][0]["name"] == "Severance"


async def test_add_torrent_unsupported(sqlite_db):
    adapter = DBAdapter(make_db_config(sqlite_db))
    r = await adapter.add_torrent("https://rutracker.org/forum/viewtopic.php?t=12345")
    assert r["error"] is True
