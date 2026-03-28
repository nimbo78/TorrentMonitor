import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from bot.config import Config
from bot.adapters.http_adapter import HTTPAdapter

pytestmark = pytest.mark.asyncio

BASE = "http://tm.local"


def make_cfg():
    return Config.load(env={
        "TELEGRAM_BOT_TOKEN": "tok",
        "TELEGRAM_ALLOWED_IDS": "1",
        "TM_ADAPTER": "http",
        "TM_HTTP_URL": BASE,
        "TM_HTTP_PASSWORD": "admin",
    })


def mock_response(body: dict, status: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    return resp


async def test_list_torrents():
    adapter = HTTPAdapter(make_cfg())
    payload = {"error": False, "msg": "", "data": [{"id": 1, "name": "Ubuntu"}]}

    with patch.object(adapter, "_post_api", new=AsyncMock(return_value=payload)):
        r = await adapter.list_torrents()
    assert r["error"] is False
    assert r["data"][0]["name"] == "Ubuntu"


async def test_pause():
    adapter = HTTPAdapter(make_cfg())
    payload = {"error": False, "msg": "", "data": None}

    with patch.object(adapter, "_post_api", new=AsyncMock(return_value=payload)) as m:
        r = await adapter.pause(42)
    m.assert_called_once_with(action="pause", id=42)
    assert r["error"] is False


async def test_resume():
    adapter = HTTPAdapter(make_cfg())
    payload = {"error": False, "msg": "", "data": None}

    with patch.object(adapter, "_post_api", new=AsyncMock(return_value=payload)) as m:
        r = await adapter.resume(42)
    m.assert_called_once_with(action="resume", id=42)
    assert r["error"] is False


async def test_delete():
    adapter = HTTPAdapter(make_cfg())
    payload = {"error": False, "msg": "", "data": None}

    with patch.object(adapter, "_post_api", new=AsyncMock(return_value=payload)) as m:
        r = await adapter.delete(7)
    m.assert_called_once_with(action="delete", id=7)
    assert r["error"] is False


async def test_add_torrent():
    adapter = HTTPAdapter(make_cfg())
    payload = {"error": False, "msg": "Тема добавлена", "data": None}

    with patch.object(adapter, "_post_api", new=AsyncMock(return_value=payload)) as m:
        r = await adapter.add_torrent("https://rutracker.org/forum/viewtopic.php?t=12345")
    assert r["error"] is False


async def test_get_new_items():
    adapter = HTTPAdapter(make_cfg())
    payload = {"error": False, "msg": "", "data": [{"id": 2, "name": "Severance"}]}

    with patch.object(adapter, "_post_api", new=AsyncMock(return_value=payload)) as m:
        r = await adapter.get_new_items("2026-03-25 00:00:00")
    m.assert_called_once_with(action="get_new_items", since="2026-03-25 00:00:00")
    assert r["data"][0]["name"] == "Severance"


async def test_network_error_returns_err():
    adapter = HTTPAdapter(make_cfg())

    with patch.object(adapter, "_post_api", new=AsyncMock(side_effect=httpx.ConnectError("refused"))):
        r = await adapter.list_torrents()
    assert r["error"] is True
    assert "refused" in r["msg"]
