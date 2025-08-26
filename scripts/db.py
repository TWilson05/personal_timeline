from pathlib import Path
import sqlite3
from typing import Iterable, Tuple

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,         -- 'photo' | 'note' | 'place' | 'strava'
    subtype TEXT,                 -- e.g., 'run','ride' for strava; 'jpeg' for photo
    ts_utc TEXT NOT NULL,         -- ISO8601 timestamp
    day TEXT NOT NULL,            -- YYYY-MM-DD (derived from ts_utc)
    lat REAL,
    lon REAL,
    path TEXT,                    -- file path for photo or GPX
    title TEXT,
    text TEXT,
    ext_id TEXT,                  -- external id (e.g., strava activity id)
    UNIQUE(source, ext_id, path) ON CONFLICT IGNORE
);

CREATE INDEX IF NOT EXISTS idx_events_day ON events(day);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts_utc);
CREATE INDEX IF NOT EXISTS idx_events_geo ON events(lat, lon);
"""


def get_conn(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_events(conn: sqlite3.Connection, rows: Iterable[Tuple]):
    sql = (
        "INSERT OR IGNORE INTO events (source, subtype, ts_utc, day, lat, lon, path, title, text, ext_id) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)"
    )
    conn.executemany(sql, rows)
    conn.commit()