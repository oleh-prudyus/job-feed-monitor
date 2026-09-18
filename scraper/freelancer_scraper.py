"""Fetches the public Freelancer.com job feed and parses listings into
JobListing objects (reusing useme_scraper's dataclass -- same shape, so
evaluator.evaluate() and bot.notify_job() work on either source unchanged).

Unlike Useme, freelancer.com/jobs/ is an Angular SPA: the raw HTML response
is an almost-empty shell, and the job cards are rendered client-side after
the page's JS runs (confirmed by hand: a plain `requests.get()` returns a
page with no job data in it at all). So every scan needs a real (headless)
browser here, not just the pagination pages like on Useme.

Job listing URLs don't reliably carry a numeric ID in the slug (e.g.
"/projects/debugging/senior-react-pwa-developer-clean" has none), so the
listing's URL path itself is used as the unique id, prefixed "fl:" to keep
it visually distinct from Useme's purely-numeric ids in the shared jobs table.
"""
import logging
import re

from playwright.sync_api import sync_playwright

from config import playwright_proxy
from scraper.useme_scraper import JobListing

logger = logging.getLogger(__name__)

JOBS_URL = "https://www.freelancer.com/jobs/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
CARD_SELECTOR = ".JobSearchCard-item"

# How long to give the page to finish its client-side render before giving up.
LOAD_TIMEOUT_MS = 20_000


def _job_id_from_href(href: str) -> str:
    return "fl:" + href.strip("/")


def _clean_budget_text(text: str) -> str:
    # The card's price block has no whitespace between the number/unit and the adjoining
    # "Avg Bid" label in the raw text content (e.g. "$101Avg Bid", "$18 / hrAvg Bid") -- add it back.
    text = re.sub(r"(?<=[\d%])(?=[A-Za-z])", " ", text)
    return re.sub(r"(?<=[a-z])(?=Avg Bid)", " ", text)


def fetch_jobs(url: str = JOBS_URL) -> list[JobListing]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy=playwright_proxy())
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(url, timeout=LOAD_TIMEOUT_MS)
            try:
                page.wait_for_selector(CARD_SELECTOR, timeout=LOAD_TIMEOUT_MS)
            except Exception:
                logger.warning("Freelancer: no job cards appeared, page may be blocked")
                return []
            html = page.content()
        finally:
            browser.close()

    return parse_jobs(html)


def parse_jobs(html: str) -> list[JobListing]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    listings = []

    for card in soup.select(CARD_SELECTOR):
        title_link = card.select_one(".JobSearchCard-primary-heading-link")
        if not title_link or not title_link.get("href"):
            continue

        href = title_link["href"]
        description_tag = card.select_one(".JobSearchCard-primary-description")
        price_tag = card.select_one(".JobSearchCard-secondary-price") or card.select_one(".JobSearchCard-primary-price")
        entry_tag = card.select_one(".JobSearchCard-secondary-entry")
        tag_links = card.select(".JobSearchCard-primary-tagsLink")

        entry_count = 0
        if entry_tag:
            digits = "".join(ch for ch in entry_tag.get_text(strip=True) if ch.isdigit())
            entry_count = int(digits) if digits else 0

        listings.append(
            JobListing(
                job_id=_job_id_from_href(href),
                title=title_link.get_text(strip=True),
                url="https://www.freelancer.com" + href,
                client_name="",  # not shown on the search-results card, only on the job page
                offers_count=entry_count,
                category=", ".join(t.get_text(strip=True) for t in tag_links),
                budget_text=_clean_budget_text(price_tag.get_text(strip=True)) if price_tag else "Negotiable",
                description=description_tag.get_text(strip=True) if description_tag else "",
            )
        )

    return listings


if __name__ == "__main__":
    for job in fetch_jobs():
        print(job.job_id, "-", job.title, "-", job.budget_text)
