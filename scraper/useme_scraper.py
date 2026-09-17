"""Fetches the public Useme job feed and parses listings into structured dicts.

Page 1 of a category feed is a plain, unauthenticated HTML page and loads fine
via `requests`. But paginated URLs (?page=2, ?page=3, ...) consistently get a
Cloudflare "Just a moment..." JS challenge (403) when hit with a bare HTTP
client -- confirmed by hand, not rate-limit-related (still blocked after a
15+ min gap). A real browser is required to clear that challenge, so
pagination goes through Playwright (same approach submitter/ already uses for
the Cloudflare-protected /login/ page) while page 1 alone still uses the
cheaper plain `requests` path.

Navigating Playwright directly to "?page=N" isn't enough, though -- confirmed
by hand that it returns byte-identical content to page 1 (same job IDs, same
order). The pagination links are plain <a href="./?page=N"> (server-rendered,
not AJAX), but a *direct* page.goto() to that URL still gets served page 1's
content -- most likely Cloudflare/the origin treating a fresh navigation
differently from an in-session link click (no referrer, fresh request
fingerprint). So pagination loads page 1 in the browser once, then clicks the
"2", "3", ... links in sequence like a real user would, waiting for each
click's navigation to finish before grabbing the HTML.
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

# Pagination (page 2+) is Cloudflare-walled -- confirmed by hand that ?page=2 shows the
# "Just a moment..." JS challenge and never resolves, whether reached by direct goto() or
# by clicking the real pagination link from an already-loaded page 1. No combination tried
# gets past it, so _fetch_pages_2plus_html() below is effectively dead weight above 1 --
# kept in place in case a future proxy/stealth change makes it worth revisiting, but for
# now we rely on scanning often (see SCAN_INTERVAL_SECONDS) to keep page 1 alone from
# missing bursts of new postings, rather than burning ~15-30s per scan on a losing fight.
PAGES_TO_FETCH = 1

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


def _first_job_href(page) -> str | None:
    link = page.locator("article.job .job__title-link").first
    return link.get_attribute("href") if link.count() else None


def _fetch_pages_2plus_html(url: str, pages: int) -> list[str]:
    """Pages 2..pages via a real (headless) browser, by clicking pagination links --
    see module docstring for why a direct page.goto("?page=N") doesn't work."""
    if pages < 2:
        return []

    html_by_page = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy=playwright_proxy())
        try:
            page = browser.new_page(user_agent=USER_AGENT)
            page.goto(url, timeout=CHALLENGE_TIMEOUT_MS)
            try:
                page.wait_for_selector("article.job", timeout=CHALLENGE_TIMEOUT_MS)
            except Exception:
                logger.warning("Page 1: no listings appeared, aborting pagination")
                return []

            # The cookie-consent banner (CookieScript) sits on top of the page and swallows
            # clicks on anything underneath it, including the pagination links -- confirmed
            # by hand: Playwright's click retries for 30s against "element intercepts pointer
            # events" and then gives up. Dismiss it once, up front, before any clicking.
            try:
                page.locator("#cookiescript_accept").click(timeout=3000)
            except Exception:
                pass  # already dismissed, or banner didn't show this time

            prev_href = _first_job_href(page)
            for page_num in range(2, pages + 1):
                link = page.locator(f'a[href*="page={page_num}"]').first
                if link.count() == 0:
                    logger.warning("Page %d: no pagination link found (last page?)", page_num)
                    break

                # The click triggers a real navigation (plain <a href>, not AJAX), so wait
                # for that navigation to finish first -- a wait_for_function evaluated
                # while navigation is in flight raises "execution context was destroyed",
                # which would otherwise look identical to "content didn't change".
                try:
                    with page.expect_navigation(timeout=CHALLENGE_TIMEOUT_MS):
                        link.click()
                    page.wait_for_selector("article.job", timeout=CHALLENGE_TIMEOUT_MS)
                except Exception:
                    logger.warning("Page %d: navigation after click failed or timed out", page_num)
                    break

                new_href = _first_job_href(page)
                if new_href == prev_href:
                    logger.warning("Page %d: content identical to previous page, stopping", page_num)
                    break

                html_by_page.append(page.content())
                prev_href = new_href
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
