"""Fetches the public Useme job feed and parses listings into structured dicts.

No login required — /en/jobs/ is a public page, so this is a plain HTML fetch,
not browser automation.
"""
import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

from config import proxy_url

JOBS_URL = "https://useme.com/en/jobs/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


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


def fetch_jobs(url: str = JOBS_URL) -> list[JobListing]:
    proxy = proxy_url()
    proxies = {"http": proxy, "https": proxy} if proxy else None
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, proxies=proxies, timeout=20)
    resp.raise_for_status()
    return parse_jobs(resp.text)


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
