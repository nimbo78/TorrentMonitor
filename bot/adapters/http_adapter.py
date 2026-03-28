from __future__ import annotations
import httpx
from bot.adapters.base import TMAdapter, ok, err
from bot.config import Config


class HTTPAdapter(TMAdapter):
    def __init__(self, config: Config):
        self._cfg = config
        self._base = config.tm_http_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
            await self._login()
        return self._client

    async def _login(self) -> None:
        resp = await self._client.post(
            f"{self._base}/action.php",
            data={"action": "enter", "password": self._cfg.tm_http_password, "remember": "false"},
        )
        resp.raise_for_status()
        body = resp.json()
        if body.get("error"):
            raise RuntimeError(f"TM login failed: {body.get('msg')}")

    async def _post_api(self, **data) -> dict:
        client = await self._get_client()
        resp = await client.post(f"{self._base}/api.php", data=data)
        resp.raise_for_status()
        return resp.json()

    async def _post_action(self, **data) -> dict:
        client = await self._get_client()
        resp = await client.post(f"{self._base}/action.php", data=data)
        resp.raise_for_status()
        return resp.json()

    async def list_torrents(self, sort_by: str = "date") -> dict:
        try:
            body = await self._post_api(action="list", sort=sort_by)
            return body
        except Exception as e:
            return err(str(e))

    async def add_torrent(self, url: str, name: str = "") -> dict:
        try:
            body = await self._post_api(action="add_torrent", url=url, name=name)
            return body
        except Exception as e:
            return err(str(e))

    async def add_serial(self, tracker: str, name: str, hd: int = 0) -> dict:
        try:
            body = await self._post_api(action="add_serial", tracker=tracker, name=name, hd=hd)
            return body
        except Exception as e:
            return err(str(e))

    async def pause(self, item_id: int) -> dict:
        try:
            body = await self._post_api(action="pause", id=item_id)
            return body
        except Exception as e:
            return err(str(e))

    async def resume(self, item_id: int) -> dict:
        try:
            body = await self._post_api(action="resume", id=item_id)
            return body
        except Exception as e:
            return err(str(e))

    async def delete(self, item_id: int) -> dict:
        try:
            body = await self._post_api(action="delete", id=item_id)
            return body
        except Exception as e:
            return err(str(e))

    async def get_warnings(self) -> dict:
        try:
            body = await self._post_api(action="get_warnings")
            return body
        except Exception as e:
            return err(str(e))

    async def get_credentials(self) -> dict:
        try:
            body = await self._post_api(action="get_credentials")
            return body
        except Exception as e:
            return err(str(e))

    async def set_credentials(self, cred_id: int, log: str, pass_: str, passkey: str) -> dict:
        try:
            body = await self._post_api(
                action="set_credentials", id=cred_id, log=log, **{"pass": pass_}, passkey=passkey
            )
            return body
        except Exception as e:
            return err(str(e))

    async def get_settings(self) -> dict:
        try:
            body = await self._post_api(action="get_settings")
            return body
        except Exception as e:
            return err(str(e))

    async def update_setting(self, key: str, value: str) -> dict:
        try:
            body = await self._post_api(action="update_setting", key=key, val=value)
            return body
        except Exception as e:
            return err(str(e))

    async def get_new_items(self, since_timestamp: str) -> dict:
        try:
            body = await self._post_api(action="get_new_items", since=since_timestamp)
            return body
        except Exception as e:
            return err(str(e))

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
