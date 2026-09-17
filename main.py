"""Entry point: runs the Telegram bot and the periodic Useme feed scan in
the same process, using python-telegram-bot's built-in job queue (so there's
no need for a second scheduler library running alongside it).
"""
import logging
from datetime import datetime, timezone

from bot.telegram_bot import build_app, notify_job
from config import SCAN_INTERVAL_SECONDS
from db import state
from evaluator.llm_evaluator import evaluate
from scraper.useme_scraper import fetch_jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def scan_job(context) -> None:
    state.set_meta("last_scan_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))

    try:
        jobs = fetch_jobs()
    except Exception:
        logger.exception("Failed to fetch Useme feed")
        state.set_meta("last_scan_ok", "0")
        return
    state.set_meta("last_scan_ok", "1")

    new_count = 0
    for job in jobs:
        if state.is_known(job.job_id):
            continue
        state.mark_seen(job.job_id, job.title, job.url)
        new_count += 1

        try:
            evaluation = evaluate(job)
        except Exception:
            logger.exception("Failed to evaluate job %s", job.job_id)
            continue

        if evaluation.is_match:
            await notify_job(context.application, job, evaluation)
        else:
            logger.info("Rejected %s (%s): %s", job.job_id, job.title, evaluation.reason)
            state.set_status(job.job_id, "rejected_auto", reason=evaluation.reason)

    state.set_meta("last_scan_new_count", str(new_count))
    if new_count:
        logger.info("Scan done: %d new listing(s) processed", new_count)


def main() -> None:
    app = build_app()
    state.set_meta("bot_started_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    app.job_queue.run_repeating(scan_job, interval=SCAN_INTERVAL_SECONDS, first=5)
    logger.info("Starting bot, scanning every %ds", SCAN_INTERVAL_SECONDS)
    app.run_polling()


if __name__ == "__main__":
    main()
