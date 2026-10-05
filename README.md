# job-feed-monitor

Monitors public freelance job feeds (Useme and Freelancer.com), scores every new listing with an
LLM against a personal set of vetting criteria, and sends the ones that match to Telegram together
with a drafted proposal in the listing's own language. You decide from the chat: mark a job as a
good fit (saved for later) or not a fit. Nothing is ever submitted automatically.

## How it works

- On a schedule (Useme: `SCAN_INTERVAL_SECONDS`, default 15 min; Freelancer.com: every 20 min) the feeds
  are fetched and any listing not seen before is processed.
- Cheap deterministic checks run first, in code (e.g. platform-specific limits on competing offers), so obviously unsuitable listings never cost an LLM call.
- The remaining listings are evaluated by Claude or OpenAI against the criteria in
  `evaluator/criteria.py`. The model returns a verdict, a one-sentence reason and, for matches,
  a draft proposal.
- Matches arrive in Telegram as a card with **Good fit / Not a fit** buttons. Saved jobs can be
  revisited with `/saved`; `/status` shows uptime, last scan and totals.
- State (which listings were seen and what happened to them) lives in SQLite and survives restarts.

## Components

```
main.py                           Entry point: Telegram bot + scheduled scans in one process
scraper/useme_scraper.py          Useme feeds, /pl/ and /en/ merged by job id (requests + BeautifulSoup)
scraper/freelancer_scraper.py     Freelancer.com skill-category feeds (Playwright)
evaluator/llm_evaluator.py        Listing evaluation + draft proposal via Claude/OpenAI
evaluator/criteria.py             Vetting criteria, kept separate from the prompt
db/state.py                       SQLite: which listings were seen / processed
bot/telegram_bot.py               Notifications, buttons, /saved and /status commands
scripts/daily_report.py           Optional daily summary sent to Telegram
```

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# fill in TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID and ANTHROPIC_API_KEY or OPENAI_API_KEY

python3 main.py
```

## Deploying to a VPS (Docker)

```bash
git clone <repo> job-feed-monitor && cd job-feed-monitor
cp .env.example .env && nano .env   # fill in tokens/keys
chmod 600 .env

docker compose up -d --build
docker compose logs -f
```

The bot opens no ports (Telegram works over outgoing long polling), so it does not conflict with
other services on the same server. An optional HTTP proxy can be configured through the
`PROXY_*` variables.

## Checklist

- [x] Public feed parsing (Useme, Polish and English feeds merged by job id)
- [x] Deterministic pre-filters in code (competition caps per platform)
- [x] LLM evaluation against vetting criteria + draft proposal
- [x] Telegram notifications with Good fit / Not a fit buttons and a `/saved` list
- [x] `/status` command: uptime, last scan, totals
- [x] Docker deployment, persistent SQLite state
- [x] Bot token no longer written to logs (HTTP client logging raised to WARNING)
- [x] Second source: Freelancer.com
- [x] Freelancehunt source removed (2026-10-02): its projects are open only to accounts
      registered in Ukraine, so a Poland-based account can't bid there
- [x] Vetting criteria updated (2026-10-05): PDF/Excel/CSV processing, Streamlit, Telegram bots and
      .NET desktop now count as a fit; captcha/login automation, 30+ hrs/week and non-Python/C# jobs rejected

## Design note: why proposals are never sent automatically

Every proposal is sent by a person. The bot's job is to cut the time spent reading listings and
to prepare a solid first draft, not to apply on someone's behalf: a proposal should reflect a
human decision that this job is worth taking.
