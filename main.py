"""Entry point: runs the Telegram bot and the periodic feed scans (Useme +
Freelancer.com) in the same process, using python-telegram-bot's built-in
job queue (so there's no need for a second scheduler library running
alongside it).
"""
import asyncio
import logging
from datetime import datetime, timezone

from bot.telegram_bot import build_app, notify_job
from config import FREELANCEHUNT_SCAN_INTERVAL_SECONDS, SCAN_INTERVAL_SECONDS
from db import state
from evaluator.llm_evaluator import evaluate
from scraper.freelancehunt_scraper import fetch_jobs as fetch_freelancehunt_jobs
from scraper.useme_scraper import fetch_jobs as fetch_useme_jobs

# Freelancer.com scanning is implemented (scraper/freelancer_scraper.py) but not
# scheduled below -- Oleh hasn't passed Freelancer's own ID verification yet, so
# there's no point surfacing jobs he can't currently bid on. Re-enable by importing
# fetch_jobs from scraper.freelancer_scraper and registering scan_freelancer_job
# again in main() once verification goes through.

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# httpx logs every request URL at INFO, and Telegram's Bot API puts the bot token in
# the URL path (/bot<TOKEN>/getUpdates) -- so the token was written to the container
# logs in plain text every 10 seconds of long-polling. WARNING still surfaces failures.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Max acceptable competing offers, per platform, checked in code before a listing
# ever reaches the LLM. Freelancer.com's bid counts run 5-10x higher than Useme's
# even on ordinary postings (confirmed live: 60-280+ bids on relevant Python/scraping
# jobs), so one shared threshold doesn't work -- and asking the LLM to apply a
# platform-relative threshold itself wasn't reliably honored (tested: gpt-4o-mini
# still rejected a 40-bid Freelancer listing for "too much competition" after being
# told 60-80 was fine there). A plain numeric check in code is deterministic instead.
#
# None = no cap. Useme's was 30 while Oleh had zero completed orders; lifted
# 2026-09-24 once he had delivered work there, since that already sets him apart
# from the zero-history bidders who make up much of a 50-80 offer pile.
COMPETITION_CAPS = {"freelancer.com": 100, "useme.com": None, "freelancehunt.com": 60}
DEFAULT_COMPETITION_CAP = 30


def _competition_cap(url: str) -> int | None:
    for domain, cap in COMPETITION_CAPS.items():
        if domain in url:
            return cap
    return DEFAULT_COMPETITION_CAP


def _freelancehunt_region_blocked(job) -> bool:
    """True if this Freelancehunt listing is very likely restricted to
    Ukraine-registered accounts, which Oleh's Poland-registered account is not.

    Confirmed live: a listing with no fixed budget on its card ("Nie podano")
    was posted with the client's own currency, UAH -- attempting to bid threw
    "Projects in UAH (Ukrainian hryvnia) are available to freelancers
    registered in Ukraine". Checked two "Nie podano" listings, both UAH-only.
    A listing WITH a fixed PLN budget on the card (e.g. "676 PLN") was postable
    normally -- the project's own currency is what gates bidding, not what
    currency individual freelancers write their counter-offers in (those varied
    regardless). Card-level budget_text is the only signal available without
    opening every listing's page, so this is a heuristic, not a certainty.
    """
    return "freelancehunt.com" in job.url and job.budget_text.strip() == "Nie podano"


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

        if _freelancehunt_region_blocked(job):
            reason = "Ймовірно доступно лише фрилансерам, зареєстрованим в Україні (валюта UAH)"
            logger.info("Rejected %s (%s): %s", job.job_id, job.title, reason)
            state.set_status(job.job_id, "rejected_auto", reason=reason)
            continue

        cap = _competition_cap(job.url)
        if cap is not None and job.offers_count > cap:
            reason = f"Забагато конкуруючих пропозицій ({job.offers_count} > {cap} для цієї платформи)"
            logger.info("Rejected %s (%s): %s", job.job_id, job.title, reason)
            state.set_status(job.job_id, "rejected_auto", reason=reason)
            continue

        try:
            evaluation = evaluate(job)
        except Exception:
            logger.exception("Failed to evaluate job %s", job.job_id)
            continue

        if evaluation.is_match:
            try:
                await notify_job(context.application, job, evaluation)
            except Exception:
                # A single bad notification (e.g. Telegram rejecting an oversized
                # callback_data) must not silently abort the rest of the scan --
                # confirmed this happened for real before rowid-based callback_data
                # replaced raw job_id (see db/state.py get_rowid docstring).
                logger.exception("Failed to notify about job %s", job.job_id)
        else:
            logger.info("Rejected %s (%s): %s", job.job_id, job.title, evaluation.reason)
            state.set_status(job.job_id, "rejected_auto", reason=evaluation.reason)

    state.set_meta(meta_count, str(new_count))
    if new_count:
        logger.info("%s scan done: %d new listing(s) processed", source_label, new_count)


async def scan_job(context) -> None:
    await _run_scan(context, "Useme", fetch_useme_jobs, "last_scan")


async def scan_freelancehunt_job(context) -> None:
    await _run_scan(context, "Freelancehunt", fetch_freelancehunt_jobs, "freelancehunt_last_scan")


def main() -> None:
    app = build_app()
    state.set_meta("bot_started_at", datetime.now(timezone.utc).isoformat(timespec="seconds"))
    app.job_queue.run_repeating(scan_job, interval=SCAN_INTERVAL_SECONDS, first=5)
    app.job_queue.run_repeating(scan_freelancehunt_job, interval=FREELANCEHUNT_SCAN_INTERVAL_SECONDS, first=15)
    logger.info(
        "Starting bot, scanning Useme every %ds and Freelancehunt every %ds",
        SCAN_INTERVAL_SECONDS,
        FREELANCEHUNT_SCAN_INTERVAL_SECONDS,
    )
    app.run_polling()


if __name__ == "__main__":
    main()
