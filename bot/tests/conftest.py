import sqlite3
import pytest

SCHEMA = """
CREATE TABLE torrent (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    tracker varchar(30) NOT NULL, name varchar(500) NOT NULL DEFAULT '',
    hd INTEGER NOT NULL DEFAULT 0, path varchar(200) NOT NULL DEFAULT '',
    torrent_id varchar(150) NOT NULL DEFAULT '', ep varchar(10) DEFAULT '',
    timestamp datetime NOT NULL DEFAULT '0000-00-00 00:00:00',
    auto_update INTEGER NOT NULL DEFAULT 0, hash varchar(40) NOT NULL DEFAULT '',
    script varchar(100) NOT NULL DEFAULT '', pause INTEGER NOT NULL DEFAULT 0,
    error INTEGER NOT NULL DEFAULT 0, closed INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    tracker varchar(30), log varchar(30), pass varchar(100),
    cookie varchar(255), passkey varchar(255),
    type varchar(32), necessarily INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    key varchar(32) NOT NULL, val varchar(100) NOT NULL
);
CREATE TABLE warning (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    time datetime NOT NULL, "where" varchar(40) NOT NULL,
    reason varchar(200) NOT NULL, t_id INTEGER DEFAULT NULL
);
"""

SEED = """
INSERT INTO credentials VALUES (1,'rutracker.org','user1','','','','forum',1);
INSERT INTO credentials VALUES (2,'lostfilm.tv','user2','','','','RSS',1);
INSERT INTO torrent VALUES
    (1,'rutracker.org','Ubuntu 24.04',0,'','12345','',
     '2026-03-20 10:00:00',0,'','',0,0,0);
INSERT INTO torrent VALUES
    (2,'lostfilm.tv','Severance',0,'','','S04E04',
     '2026-03-28 22:36:00',0,'','',0,0,0);
INSERT INTO settings VALUES (1,'proxy','0');
INSERT INTO settings VALUES (2,'proxyAddress','127.0.0.1:9050');
INSERT INTO warning VALUES (1,'2026-03-28 12:00:00','rutracker.org','cookie_expired',NULL);
"""


@pytest.fixture
def sqlite_db(tmp_path):
    db_path = str(tmp_path / "tm.sqlite")
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA + SEED)
    conn.commit()
    conn.close()
    return db_path


def make_db_config(db_path: str):
    from bot.config import Config
    return Config.load(env={
        "TELEGRAM_BOT_TOKEN": "tok",
        "TELEGRAM_ALLOWED_IDS": "1",
        "TM_ADAPTER": "db",
        "TM_DB_TYPE": "sqlite",
        "TM_DB_PATH": db_path,
    })
