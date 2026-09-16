"""SQLite-backed tracking of seen jobs so the bot never notifies twice."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "bot_state.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'seen',  -- seen | notified | approved | rejected | sent | failed
    draft_offer TEXT,
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def is_known(job_id: str) -> bool:
    with connect() as conn:
        row = conn.execute("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return row is not None


def mark_seen(job_id: str, title: str, url: str, status: str = "seen"):
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO jobs (job_id, title, url, status) VALUES (?, ?, ?, ?)",
            (job_id, title, url, status),
        )


def set_status(job_id: str, status: str, draft_offer: str | None = None):
    with connect() as conn:
        if draft_offer is not None:
            conn.execute(
                "UPDATE jobs SET status = ?, draft_offer = ?, updated_at = datetime('now') WHERE job_id = ?",
                (status, draft_offer, job_id),
            )
        else:
            conn.execute(
                "UPDATE jobs SET status = ?, updated_at = datetime('now') WHERE job_id = ?",
                (status, job_id),
            )


def get_job(job_id: str) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
