"""Fetches Freelancehunt.com skill-page job feeds and parses listings into
JobListing objects (reusing useme_scraper's dataclass -- same shape, so
evaluator.evaluate() and bot.notify_job() work on this source unchanged).

Like Freelancer.com, freelancehunt.com sits behind Cloudflare -- confirmed
by hand: a plain `requests.get()` gets a 403 with a JS challenge page, even
with a normal browser User-Agent. So this goes through a real (headless)
browser via Playwright, same as freelancer_scraper.py. Unlike Freelancer.com
though, the job cards themselves ARE present in the server-rendered HTML
once past the challenge (no client-side JS re-render needed) -- confirmed
by inspecting the live DOM (`.widget.project-card` articles carry title,
skills, budget, offer count and description directly).

There's no single combined "IT & Programming" feed, only per-skill pages
(/projects/skill/<slug>/<id>.html), so this scans a short list of skill
pages matching Oleh's stack -- same approach as freelancer_scraper.py's
CATEGORY_SLUGS, for the same reason (avoid drowning in off-skill postings).
"""
import logging
import re

from playwright.sync_api import sync_playwright

from config import playwright_proxy
from scraper.useme_scraper import JobListing

logger = logging.getLogger(__name__)

# skill slug -> Freelancehunt's numeric skill id, both required to build the URL.
# Matches Oleh's stack (see evaluator/criteria.py SKILLS): Python, C#, and data
# parsing/scraping specifically (closest match to "web scraping" as a skill page).
CATEGORIES = {
    "python": "22",
    "c": "24",  # C# -- Freelancehunt's slug is just "c", not "c-sharp"
    "parsowanie-danych": "169",  # data parsing/scraping
}
JOBS_URL_TEMPLATE = "https://freelancehunt.com/pl/projects/skill/{slug}/{id}.html"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
CARD_SELECTOR = "article.project-card"

# How long to give the Cloudflare challenge to resolve and the page to render
# before giving up on a given category page.
LOAD_TIMEOUT_MS = 20_000


def _job_id_from_href(href: str) -> str:
    # URLs look like .../project/<slug>/<numeric-id>.html
    match = re.search(r"/(\d+)\.html/?$", href)
    return "fh:" + (match.group(1) if match else href.strip("/"))


def _fetch_category_html(page, slug: str, skill_id: str) -> str | None:
    url = JOBS_URL_TEMPLATE.format(slug=slug, id=skill_id)
    page.goto(url, timeout=LOAD_TIMEOUT_MS)
    try:
        page.wait_for_selector(CARD_SELECTOR, timeout=LOAD_TIMEOUT_MS)
    except Exception:
        logger.warning("Freelancehunt category '%s': no job cards appeared, page may be blocked", slug)
        return None
    return page.content()


def fetch_jobs(categories: dict[str, str] = CATEGORIES) -> list[JobListing]:
    listings: list[JobListing] = []
    seen_ids: set[str] = set()

    with sync_playwright() as p:
        # Tried headless=False (via Xvfb) to see if Cloudflare's challenge on the
        # "python" and "parsowanie-danych" category pages was fingerprinting headless
        # mode specifically -- it wasn't: still blocked, identically, in headed mode.
        # Confirmed by hand that navigator.webdriver was the more likely tell (true
        # by default in Playwright), so the init script below spoofs it regardless of
        # headless/headed -- but even with that spoofed, the challenge still didn't
        # clear. Whatever Cloudflare is keying on here (TLS/canvas/timing fingerprint,
        # most likely) isn't fixed by either of those, so this stays headless=True:
        # same result, without the extra Xvfb/resource overhead for no benefit.
        browser = p.chromium.launch(headless=True, proxy=playwright_proxy())
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
            for slug, skill_id in categories.items():
                html = _fetch_category_html(page, slug, skill_id)
                if html is None:
                    continue
                for job in parse_jobs(html):
                    if job.job_id not in seen_ids:
                        seen_ids.add(job.job_id)
                        listings.append(job)
        finally:
            browser.close()

    return listings


def parse_jobs(html: str) -> list[JobListing]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    listings = []

    for card in soup.select(CARD_SELECTOR):
        title_link = card.select_one("h2 a.project-link")
        if not title_link or not title_link.get("href"):
            continue

        href = title_link["href"]
        skill_links = card.select(".project-skills a.project-skill")
        stat_spans = card.select(".project-stats .project-stat")
        budget_tag = card.select_one(".project-stats .project-stat.budget")
        description_tag = card.select_one(".project-description")

        # The offer-count stat is whichever .project-stat isn't the budget one --
        # budget is absent entirely ("Nie podano" isn't even rendered as a span
        # on some cards), so index-based lookup isn't reliable.
        offers_text = ""
        for stat in stat_spans:
            if stat is not budget_tag:
                offers_text = stat.get_text(strip=True)
                break
        digits = "".join(ch for ch in offers_text if ch.isdigit())
        offers_count = int(digits) if digits else 0

        listings.append(
            JobListing(
                job_id=_job_id_from_href(href),
                title=title_link.get_text(strip=True),
                url=href,
                client_name="",  # not shown on the listing card, only on the job page
                offers_count=offers_count,
                category=", ".join(s.get_text(strip=True) for s in skill_links),
                budget_text=budget_tag.get_text(strip=True) if budget_tag else "Nie podano",
                description=description_tag.get_text(strip=True) if description_tag else "",
            )
        )

    return listings


if __name__ == "__main__":
    for job in fetch_jobs():
        print(job.job_id, "-", job.title, "-", job.budget_text)
