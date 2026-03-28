from __future__ import annotations
import asyncio
import sqlite3
from bot.adapters.base import TMAdapter, ok, err
from bot.config import Config


class DBAdapter(TMAdapter):
    def __init__(self, config: Config):
        self._cfg = config

    def _connect(self):
        """Returns (connection, placeholder_char)."""
        db_type = self._cfg.tm_db_type
        if db_type == "sqlite":
            conn = sqlite3.connect(self._cfg.tm_db_path)
            conn.row_factory = sqlite3.Row
            return conn, "?"
        if db_type == "mysql":
            import pymysql
            conn = pymysql.connect(
                host=self._cfg.tm_db_host,
                port=self._cfg.tm_db_port,
                db=self._cfg.tm_db_name,
                user=self._cfg.tm_db_user,
                password=self._cfg.tm_db_password,
                cursorclass=pymysql.cursors.DictCursor,
                charset="utf8mb4",
            )
            return conn, "%s"
        if db_type in ("pgsql", "postgresql"):
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(
                host=self._cfg.tm_db_host,
                port=self._cfg.tm_db_port,
                dbname=self._cfg.tm_db_name,
                user=self._cfg.tm_db_user,
                password=self._cfg.tm_db_password,
                cursor_factory=psycopg2.extras.RealDictCursor,
            )
            return conn, "%s"
        raise ValueError(f"Unknown DB type: {db_type}")

    def _adapt(self, sql: str, ph: str) -> str:
        """Swap ? to ph, fix `where` quoting for MySQL."""
        if ph != "?":
            sql = sql.replace("?", ph)
        if self._cfg.tm_db_type == "mysql":
            sql = sql.replace('"where"', "`where`")
        return sql

    def _query(self, sql: str, params: tuple = ()) -> list[dict]:
        conn, ph = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(self._adapt(sql, ph), params)
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()

    def _exec(self, sql: str, params: tuple = ()) -> None:
        conn, ph = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(self._adapt(sql, ph), params)
            conn.commit()
        finally:
            conn.close()

    async def list_torrents(self, sort_by: str = "date") -> dict:
        order = "t.timestamp DESC" if sort_by == "date" else "t.name ASC"
        sql = f"""
            SELECT t.id, t.name, t.tracker, t.torrent_id, t.ep,
                   t.timestamp, t.pause,
                   COALESCE(c.type, '') AS type
            FROM torrent t
            LEFT JOIN credentials c ON c.tracker = t.tracker
            ORDER BY {order}
        """
        try:
            data = await asyncio.to_thread(self._query, sql)
            return ok(data)
        except Exception as e:
            return err(str(e))

    async def add_torrent(self, url: str, name: str = "") -> dict:
        return err("add_torrent not supported via DB adapter — use HTTP adapter")

    async def add_serial(self, tracker: str, name: str, hd: int = 0) -> dict:
        return err("add_serial not supported via DB adapter — use HTTP adapter")

    async def pause(self, item_id: int) -> dict:
        try:
            await asyncio.to_thread(self._exec, "UPDATE torrent SET pause=1 WHERE id=?", (item_id,))
            return ok()
        except Exception as e:
            return err(str(e))

    async def resume(self, item_id: int) -> dict:
        try:
            await asyncio.to_thread(self._exec, "UPDATE torrent SET pause=0 WHERE id=?", (item_id,))
            return ok()
        except Exception as e:
            return err(str(e))

    async def delete(self, item_id: int) -> dict:
        try:
            await asyncio.to_thread(self._exec, "DELETE FROM torrent WHERE id=?", (item_id,))
            return ok()
        except Exception as e:
            return err(str(e))

    async def get_warnings(self) -> dict:
        sql = 'SELECT id, time, "where" AS location, reason FROM warning ORDER BY time DESC'
        try:
            data = await asyncio.to_thread(self._query, sql)
            return ok(data)
        except Exception as e:
            return err(str(e))

    async def get_credentials(self) -> dict:
        sql = "SELECT id, tracker, log, type, necessarily FROM credentials"
        try:
            data = await asyncio.to_thread(self._query, sql)
            return ok(data)
        except Exception as e:
            return err(str(e))

    async def set_credentials(self, cred_id: int, log: str, pass_: str, passkey: str) -> dict:
        sql = "UPDATE credentials SET log=?, pass=?, passkey=? WHERE id=?"
        try:
            await asyncio.to_thread(self._exec, sql, (log, pass_, passkey, cred_id))
            return ok()
        except Exception as e:
            return err(str(e))

    async def get_settings(self) -> dict:
        try:
            rows = await asyncio.to_thread(self._query, "SELECT key, val FROM settings")
            return ok({r["key"]: r["val"] for r in rows})
        except Exception as e:
            return err(str(e))

    async def update_setting(self, key: str, value: str) -> dict:
        try:
            await asyncio.to_thread(self._exec, "UPDATE settings SET val=? WHERE key=?", (value, key))
            return ok()
        except Exception as e:
            return err(str(e))

    async def get_new_items(self, since_timestamp: str) -> dict:
        sql = """
            SELECT t.id, t.name, t.tracker, t.torrent_id, t.ep,
                   t.timestamp, t.pause,
                   COALESCE(c.type, '') AS type
            FROM torrent t
            LEFT JOIN credentials c ON c.tracker = t.tracker
            WHERE t.timestamp > ?
            ORDER BY t.timestamp DESC
        """
        try:
            data = await asyncio.to_thread(self._query, sql, (since_timestamp,))
            return ok(data)
        except Exception as e:
            return err(str(e))
