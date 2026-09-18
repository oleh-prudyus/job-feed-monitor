"""Entry point: runs the Telegram bot and the periodic feed scans (Useme +
Freelancer.com) in the same process, using python-telegram-bot's built-in
job queue (so there's no need for a second scheduler library running
alongside it).
"""
import asyncio
import logging
from datetime import datetime, timezone

from bot.telegram_bot import build_app, notify_job
from config import FREELANCER_SCAN_INTERVAL_SECONDS, SCAN_INTERVAL_SECONDS
from db import state
from evaluator.llm_evaluator import evaluate
from scraper.freelancer_scraper import fetch_jobs as fetch_freelancer_jobs
from scraper.useme_scraper import fetch_jobs as fetch_useme_jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


async def _run_scan(context, source_label: str, fetch_fn, meta_prefix: str) -> None:
    meta_at, meta_ok, meta_count = f"{meta_prefix}_at", f"{meta_prefix}_ok", f"{meta_prefix}_new_count"
    state.set_meta(meta_at, datetime.now(timezone.utc).isoformat(timespec="seconds"))

    try:
        # Both scrapers use Playwright's sync API internally, which refuses to run in a
        # thread that already has an asyncio event loop -- and this whole function runs
        # inside python-telegram-bot's loop. A plain worker thread sidesteps that.
        jobs = await asyncio.to_thread(fetch_fn)
    except Exception:
        logger.exception("Failed to fetch %s feed", source_label)
        state.set_meta(meta_ok, "0")
        return
    state.set_meta(meta_ok, "1")

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

    state.set_meta(meta_count, str(new_count))
    if new_count:
        logger.info("%s scan done: %d new listing(s) processed", source_label, new_count)


async def scan_job(context) -> None:
    await _run_scan(context, "Useme", fetch_useme_jobs, "last_scan")


async def scan_freelancer_job(context) -> None:
    await _run_scan(context, "Freelancer", fetch_freelancer_jobs, "freelancer_last_scan")


def main() -> None:
    app = build_app()
    state.set_meta("bot_started_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    app.job_queue.run_repeating(scan_job, interval=SCAN_INTERVAL_SECONDS, first=5)
    app.job_queue.run_repeating(scan_freelancer_job, interval=FREELANCER_SCAN_INTERVAL_SECONDS, first=15)
    logger.info(
        "Starting bot, scanning Useme every %ds and Freelancer every %ds",
        SCAN_INTERVAL_SECONDS,
        FREELANCER_SCAN_INTERVAL_SECONDS,
    )
    app.run_polling()


if __name__ == "__main__":
    main()
