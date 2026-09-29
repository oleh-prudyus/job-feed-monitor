# Working notes — status & remaining tasks

Internal tracker, not part of the public README.

## Done
- [x] Useme feed scraper (`scraper/useme_scraper.py`), verified against the live page
- [x] SQLite state (`db/state.py`)
- [x] LLM evaluator + criteria (`evaluator/`)
- [x] Telegram bot: notifications + buttons (`bot/telegram_bot.py`)
- [x] `main.py` orchestration: python-telegram-bot job queue (no separate APScheduler) + bot startup
- [x] Docker image (`docker/Dockerfile`, base image with preinstalled Chromium) + `docker-compose.yml`
- [x] Deployed on a VPS as a separate compose stack; no ports used; SQLite persists across restarts
- [x] `/status` command: uptime, last scan, new jobs found, next scan, per-status breakdown
      (needed a new `meta` table in `db/state.py` to store the last scan time)
- [x] Git-based deploy on the VPS (read-only deploy key): update = `git pull` + `docker compose up -d --build`
- [x] Optional proxy support: scraper and any Playwright code use the same `config.proxy_url()`
- [x] Second source: Freelancehunt (Playwright)
- [x] Polish feed (`/pl/`) scanned alongside the English one — the English feed alone lists only a
      handful of postings, so the bot had been reporting "0 new" for days
- [x] Competition cap lifted for Useme (kept for the other platforms)
- [x] Freelancer.com re-enabled as a third source (2026-09-29, after ID verification passed)
- [x] Bot token no longer leaks into logs (httpx logs request URLs, and Telegram puts the token in the URL)

## Remaining
- [ ] Freelancehunt: intermittently blocked by Cloudflare ("no job cards appeared") — monitoring only
- [ ] The evaluator only sees the short description shown in the feed, not attachments or the full
      page; long specs (e.g. a linked requirements file) can lead to a wrong "match"
