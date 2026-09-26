"""Sends a daily summary to Telegram: bot health + new jobs seen in the last 24h.

Runs standalone (not through main.py/python-telegram-bot) so it can be triggered by a
plain host crontab entry via `docker compose exec`, independent of whether the bot's
own scan loop or anyone's laptop is running -- see NOTES on why this replaced trying
to check bot health from a local Claude session (needs a local SSH key that isn't
available if the laptop is off).
"""
import sqlite3
from datetime import datetime, timedelta, timezone

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from db.state import DB_PATH


def build_report() -> str:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    meta = {row["key"]: row["value"] for row in conn.execute("SELECT key, value FROM meta")}
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="seconds")

    new_24h = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE first_seen_at >= ?", (since,)
    ).fetchone()[0]
    matches_24h = conn.execute(
        "SELECT COUNT(*) FROM jobs WHERE first_seen_at >= ? AND status != 'rejected_auto'",
        (since,),
    ).fetchone()[0]
    matches = conn.execute(
        "SELECT title, url, status FROM jobs WHERE first_seen_at >= ? AND status != 'rejected_auto' ORDER BY first_seen_at DESC",
        (since,),
    ).fetchall()
    conn.close()

    ok = meta.get("last_scan_ok") == "1"
    lines = [
        "\U0001f4ca *job-feed-monitor -- daily report*",
        "",
        f"Scan status: {'✅ OK' if ok else '⚠️ errors'}",
        f"Last scan: {meta.get('last_scan_at', 'unknown')}",
        f"New jobs in 24h: {new_24h}",
        f"Of which relevant: {matches_24h}",
    ]
    if matches:
        lines.append("")
        lines.append("Relevant jobs:")
        for m in matches:
            lines.append(f"- [{m['title']}]({m['url']}) ({m['status']})")

    return "\n".join(lines)


def send(text: str) -> None:
    resp = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        },
        timeout=15,
    )
    resp.raise_for_status()


if __name__ == "__main__":
    send(build_report())
