from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


def _load_env_file() -> None:
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)


@dataclass
class Config:
    bot_token: str
    allowed_ids: set[int]
    tm_adapter: str
    tm_http_url: str
    tm_http_password: str
    tm_db_type: str
    tm_db_path: str
    tm_db_host: str
    tm_db_port: int
    tm_db_name: str
    tm_db_user: str
    tm_db_password: str
    page_size: int
    poll_interval: int
    tmdb_api_key: str

    @classmethod
    def load(cls, env: dict | None = None) -> "Config":
        if env is None:
            _load_env_file()
            env = os.environ

        token = env.get("TELEGRAM_BOT_TOKEN")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")

        raw_ids = env.get("TELEGRAM_ALLOWED_IDS", "")
        if not raw_ids:
            raise ValueError("TELEGRAM_ALLOWED_IDS is required")
        allowed_ids = {int(x.strip()) for x in raw_ids.split(",") if x.strip()}

        return cls(
            bot_token=token,
            allowed_ids=allowed_ids,
            tm_adapter=env.get("TM_ADAPTER", "http"),
            tm_http_url=env.get("TM_HTTP_URL", "http://localhost:80"),
            tm_http_password=env.get("TM_HTTP_PASSWORD", "admin"),
            tm_db_type=env.get("TM_DB_TYPE", "sqlite"),
            tm_db_path=env.get("TM_DB_PATH", "/data/htdocs/db/tm.sqlite"),
            tm_db_host=env.get("TM_DB_HOST", "localhost"),
            tm_db_port=int(env.get("TM_DB_PORT", "3306")),
            tm_db_name=env.get("TM_DB_NAME", "torrentmonitor"),
            tm_db_user=env.get("TM_DB_USER", "torrentmonitor"),
            tm_db_password=env.get("TM_DB_PASSWORD", ""),
            page_size=int(env.get("TM_PAGE_SIZE", "10")),
            poll_interval=int(env.get("TM_POLL_INTERVAL", "300")),
            tmdb_api_key=env.get("TMDB_API_KEY", ""),
        )
