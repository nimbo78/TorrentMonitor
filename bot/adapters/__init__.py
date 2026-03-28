from bot.config import Config
from bot.adapters.base import TMAdapter


def make_adapter(config: Config) -> TMAdapter:
    if config.tm_adapter == "db":
        from bot.adapters.db_adapter import DBAdapter
        return DBAdapter(config)
    from bot.adapters.http_adapter import HTTPAdapter
    return HTTPAdapter(config)
