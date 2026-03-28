from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


def ok(data: Any = None, msg: str = "") -> dict:
    return {"error": False, "msg": msg, "data": data}


def err(msg: str) -> dict:
    return {"error": True, "msg": msg, "data": None}


class TMAdapter(ABC):
    """All methods return {"error": bool, "msg": str, "data": ...}."""

    @abstractmethod
    async def list_torrents(self, sort_by: str = "date") -> dict:
        """data: list[dict] {id, name, tracker, torrent_id, ep, timestamp, pause, type}"""

    @abstractmethod
    async def add_torrent(self, url: str, name: str = "") -> dict:
        """data: None"""

    @abstractmethod
    async def add_serial(self, tracker: str, name: str, hd: int = 0) -> dict:
        """data: None"""

    @abstractmethod
    async def pause(self, item_id: int) -> dict:
        """data: None"""

    @abstractmethod
    async def resume(self, item_id: int) -> dict:
        """data: None"""

    @abstractmethod
    async def delete(self, item_id: int) -> dict:
        """data: None"""

    @abstractmethod
    async def get_warnings(self) -> dict:
        """data: list[dict] {id, time, location, reason}"""

    @abstractmethod
    async def get_credentials(self) -> dict:
        """data: list[dict] {id, tracker, log, type, necessarily} — no passwords"""

    @abstractmethod
    async def set_credentials(self, cred_id: int, log: str, pass_: str, passkey: str) -> dict:
        """data: None"""

    @abstractmethod
    async def get_settings(self) -> dict:
        """data: dict key→value"""

    @abstractmethod
    async def update_setting(self, key: str, value: str) -> dict:
        """data: None"""

    @abstractmethod
    async def get_new_items(self, since_timestamp: str) -> dict:
        """data: list[dict] same shape as list_torrents, filtered by timestamp > since"""
