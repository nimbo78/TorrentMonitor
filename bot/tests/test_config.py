import pytest
from bot.config import Config


def test_missing_token_raises():
    with pytest.raises(ValueError, match="TELEGRAM_BOT_TOKEN"):
        Config.load(env={})


def test_missing_allowed_ids_raises():
    with pytest.raises(ValueError, match="TELEGRAM_ALLOWED_IDS"):
        Config.load(env={"TELEGRAM_BOT_TOKEN": "tok"})


def test_defaults():
    cfg = Config.load(env={
        "TELEGRAM_BOT_TOKEN": "tok",
        "TELEGRAM_ALLOWED_IDS": "123,456",
    })
    assert cfg.tm_adapter == "http"
    assert cfg.page_size == 10
    assert cfg.poll_interval == 300
    assert cfg.tmdb_api_key == ""
    assert cfg.allowed_ids == {123, 456}


def test_db_adapter_config():
    cfg = Config.load(env={
        "TELEGRAM_BOT_TOKEN": "tok",
        "TELEGRAM_ALLOWED_IDS": "1",
        "TM_ADAPTER": "db",
        "TM_DB_TYPE": "mysql",
        "TM_DB_HOST": "myhost",
        "TM_DB_PORT": "3307",
    })
    assert cfg.tm_adapter == "db"
    assert cfg.tm_db_type == "mysql"
    assert cfg.tm_db_host == "myhost"
    assert cfg.tm_db_port == 3307
