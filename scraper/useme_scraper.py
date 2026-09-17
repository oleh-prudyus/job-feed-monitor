"""Fetches the public Useme job feed and parses listings into structured dicts.

Page 1 of a category feed is a plain, unauthenticated HTML page and loads fine
via `requests`. But paginated URLs (?page=2, ?page=3, ...) consistently get a
Cloudflare "Just a moment..." JS challenge (403) when hit with a bare HTTP
client -- confirmed by hand, not rate-limit-related (still blocked after a
15+ min gap). A real browser is required to clear that challenge, so
pagination goes through Playwright (same approach submitter/ already uses for
the Cloudflare-protected /login/ page) while page 1 alone still uses the
cheaper plain `requests` path.
"""
import logging
import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from config import playwright_proxy, proxy_url

logger = logging.getLogger(__name__)

JOBS_URL = "https://useme.com/en/jobs/category/programming-i-it,2/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Only page 1 ("newest" sort) used to be fetched -- a burst of >20 postings between two
# scans (30 min apart in the worst case) would push older-but-still-unseen listings off
# it before the bot ever looked, silently skipping them forever (db.is_known() never
# gets a chance to record them). Fetching a few pages gives real headroom against that.
PAGES_TO_FETCH = 3

# How long to give the Cloudflare interstitial to resolve and redirect to the real
# page before giving up on a given pagination request, in milliseconds.
CHALLENGE_TIMEOUT_MS = 15_000


@dataclass
class JobListing:
    job_id: str
    title: str
    url: str
    client_name: str
    offers_count: int
    category: str
    budget_text: str
    description: str


def _extract_job_id(url: str) -> str:
    # URLs look like /en/jobs/<slug>,<id>/
    match = re.search(r",(\d+)/?$", url)
    return match.group(1) if match else url


def _fetch_page1_html(url: str) -> str:
    proxy = proxy_url()
    proxies = {"http": proxy, "https": proxy} if proxy else None
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, proxies=proxies, timeout=20)
    resp.raise_for_status()
    return resp.text


def _fetch_pages_2plus_html(url: str, pages: int) -> list[str]:
    """Pages 2..pages via a real (headless) browser -- see module docstring for why."""
    if pages < 2:
        return []

    html_by_page = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy=playwright_proxy())
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            for page_num in range(2, pages + 1):
                page.goto(f"{url}?page={page_num}", timeout=CHALLENGE_TIMEOUT_MS)
                # The Cloudflare interstitial replaces itself with the real page via JS once
                # it resolves; wait for a real listing to show up (or time out if this page
                # genuinely has none, e.g. we've paged past the last one).
                try:
                    page.wait_for_selector("article.job", timeout=CHALLENGE_TIMEOUT_MS)
                except Exception:
                    logger.warning("Page %d: no listings appeared (Cloudflare challenge or last page)", page_num)
                    break
                html_by_page.append(page.content())
        finally:
            browser.close()
    return html_by_page


def fetch_jobs(url: str = JOBS_URL, pages: int = PAGES_TO_FETCH) -> list[JobListing]:
    all_html = [_fetch_page1_html(url)]
    all_html.extend(_fetch_pages_2plus_html(url, pages))

    listings: list[JobListing] = []
    seen_ids: set[str] = set()
    for html in all_html:
        for job in parse_jobs(html):
            if job.job_id not in seen_ids:
                seen_ids.add(job.job_id)
                listings.append(job)
    return listings


def parse_jobs(html: str) -> list[JobListing]:
    soup = BeautifulSoup(html, "html.parser")
    listings = []

    for article in soup.select("article.job"):
        title_link = article.select_one(".job__title-link")
        if not title_link:
            continue

        url = "https://useme.com" + title_link["href"]
        client_name_tag = article.select_one("strong[aria-label]")
        offers_tag = article.select_one(".job__header-details--offers span:last-child")
        category_tag = article.select_one(".job__category p")
        budget_tag = article.select_one(".job__budget-value")
        description_tag = article.select_one(".job__content p")

        listings.append(
            JobListing(
                job_id=_extract_job_id(url),
                title=title_link.get_text(strip=True),
                url=url,
                client_name=client_name_tag.get_text(strip=True) if client_name_tag else "",
                offers_count=int(offers_tag.get_text(strip=True)) if offers_tag and offers_tag.get_text(strip=True).isdigit() else 0,
                category=category_tag.get_text(strip=True) if category_tag else "",
                budget_text=budget_tag.get_text(strip=True) if budget_tag else "Negotiable",
                description=description_tag.get_text(strip=True) if description_tag else "",
            )
        )

    return listings


if __name__ == "__main__":
    for job in fetch_jobs():
        print(job.job_id, "-", job.title, "-", job.budget_text)
