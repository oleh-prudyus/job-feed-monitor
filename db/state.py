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
    status TEXT NOT NULL DEFAULT 'seen',  -- seen | notified | approved | rejected | rejected_auto | sent | failed
    draft_offer TEXT,
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Small key/value store for bot-wide facts (last scan time, uptime, ...)
-- that don't belong to any single job.
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@contextmanager
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
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


def set_meta(key: str, value: str):
    with connect() as conn:
        conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )


def get_meta(key: str) -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None


def status_counts() -> dict[str, int]:
    with connect() as conn:
        rows = conn.execute("SELECT status, COUNT(*) AS c FROM jobs GROUP BY status").fetchall()
        return {r["status"]: r["c"] for r in rows}


def total_jobs() -> int:
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) AS c FROM jobs").fetchone()["c"]
