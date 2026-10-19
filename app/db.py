"""SQLite storage for 51/51. One small file, created on startup."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DB_PATH = DATA_DIR / "5151.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS couples (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    is_sample INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS partners (
    id INTEGER PRIMARY KEY,
    couple_id INTEGER NOT NULL REFERENCES couples(id),
    key TEXT UNIQUE NOT NULL,          -- secret saved in this partner's browser
    name TEXT NOT NULL,
    colour TEXT NOT NULL,
    kids_count INTEGER,
    kids_ages TEXT,
    material TEXT NOT NULL,            -- JSON, PRIVATE to this partner's agent
    immaterial TEXT NOT NULL,          -- JSON, PRIVATE
    extra_note TEXT NOT NULL DEFAULT '', -- PRIVATE
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY,
    couple_id INTEGER NOT NULL REFERENCES couples(id),
    partner_id INTEGER NOT NULL REFERENCES partners(id),
    created_at TEXT NOT NULL,          -- UTC, ISO format
    kind TEXT NOT NULL,                -- text | photo
    text TEXT NOT NULL DEFAULT '',     -- what the partner typed (if anything)
    area TEXT NOT NULL,                -- kids | home | money | unsorted
    summary TEXT NOT NULL              -- what is shown on Today
);
CREATE TABLE IF NOT EXISTS board_cache (
    couple_id INTEGER NOT NULL,
    week_start TEXT NOT NULL,
    fingerprint TEXT NOT NULL,         -- changes when entries or partners change
    data TEXT NOT NULL,                -- JSON board incl. one message per partner
    PRIMARY KEY (couple_id, week_start)
);
CREATE TABLE IF NOT EXISTS conflicts (
    id INTEGER PRIMARY KEY,
    couple_id INTEGER NOT NULL REFERENCES couples(id),
    partner_id INTEGER NOT NULL REFERENCES partners(id),
    question TEXT NOT NULL,
    reply TEXT NOT NULL,
    nudge TEXT,                        -- kind suggestion shown to the OTHER partner (never the complaint)
    created_at TEXT NOT NULL
);
"""


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.executescript(SCHEMA)
        cols = [r[1] for r in db.execute("PRAGMA table_info(conflicts)")]
        if "nudge" not in cols:  # databases created before nudges existed
            db.execute("ALTER TABLE conflicts ADD COLUMN nudge TEXT")


@contextmanager
def connect():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    finally:
        db.close()
