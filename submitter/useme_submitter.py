"""Submits an offer on Useme using a saved login session (see
scripts/save_session.py — the login itself is never automated, only reused
from a session created by logging in manually; see README for why).

Field selectors and the copyright radio values were confirmed by inspecting
the real "Post a job offer" form (/en/jobs/<id>/offer/start/):
  - description: a contenteditable rich-text div, NOT a plain textarea —
    it silently drops input from JS-level insertion (execCommand); only a
    real, event-by-event keystroke simulation (Playwright's `.type()`)
    reliably reaches the hidden #id_description field the editor syncs into.
  - copyright_transfer radios: value="without" is "No copyright transfer"
    (kept default — safest choice for freelance gigs unless a listing says
    otherwise).
  - price: #id_payment, currency: #id_currency (select), workdays: #id_work_days.
  - Step 1 submit: button "Go to summary". Step 2 (summary) has its own
    final confirm button — selector kept generic (last submit button on the
    page) since the exact label wasn't confirmed without risking a real send;
    verify it once by hand on the first real run before trusting it blindly.
"""
import logging
from pathlib import Path

from playwright.sync_api import sync_playwright

from config import PROXY_HOST, PROXY_PASSWORD, PROXY_PORT, PROXY_USERNAME

logger = logging.getLogger(__name__)

SESSION_PATH = Path(__file__).parent.parent / "storage_state.json"


def _playwright_proxy() -> dict | None:
    """Playwright wants host/user/pass as separate fields, not one URL."""
    if not PROXY_HOST:
        return None
    proxy = {"server": f"http://{PROXY_HOST}:{PROXY_PORT}"}
    if PROXY_USERNAME:
        proxy["username"] = PROXY_USERNAME
        proxy["password"] = PROXY_PASSWORD
    return proxy


def submit_offer(
    job_id: str,
    job_url: str,
    offer_text: str,
    price: int = 0,
    currency: str = "PLN",
    workdays: int = 7,
) -> None:
    """Fills and submits the offer form for a Useme job.

    Raises on any failure (missing/expired session, unexpected page state) —
    bot/telegram_bot.py wraps calls to this in try/except and reports
    failures back to Oleh in Telegram, so errors here should be loud, not
    swallowed.
    """
    if not SESSION_PATH.exists():
        raise RuntimeError(
            "storage_state.json missing — run scripts/save_session.py locally "
            "and copy the file next to this bot's .env"
        )

    offer_url = f"https://useme.com/en/jobs/{job_id}/offer/start/"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, proxy=_playwright_proxy())
        context = browser.new_context(storage_state=str(SESSION_PATH))
        page = context.new_page()

        page.goto(offer_url, wait_until="networkidle")

        if "login" in page.url:
            raise RuntimeError(
                "Useme session expired — re-run scripts/save_session.py and "
                "redeploy storage_state.json"
            )

        # --- Step 1: describe the offer ---
        editable = page.locator('div[contenteditable="true"]').first
        editable.click()
        editable.type(offer_text, delay=5)

        page.locator('input[name="copyright_transfer"][value="without"]').check()

        if price:
            page.fill("#id_payment", str(price))
        page.select_option("#id_currency", currency)
        page.fill("#id_work_days", str(workdays))

        page.get_by_role("button", name="Go to summary").click()
        page.wait_for_load_state("networkidle")

        if page.locator("text=This field is required").count() > 0:
            browser.close()
            raise RuntimeError(
                "Useme rejected the offer form (field validation) — "
                "check that the description actually got typed in"
            )

        # --- Step 2: summary / final confirm ---
        # Exact label unconfirmed to avoid firing a real test offer during
        # development — verify this selector on the first real approval and
        # adjust if it clicks the wrong thing.
        confirm_button = page.locator('button[type="submit"]').last
        confirm_button.click()
        page.wait_for_load_state("networkidle")

        logger.info("Offer submitted for job %s, final URL: %s", job_id, page.url)
        browser.close()
