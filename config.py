import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])

USEME_EMAIL = os.environ.get("USEME_EMAIL")
USEME_PASSWORD = os.environ.get("USEME_PASSWORD")

# How often to re-scan the feed, in seconds.
SCAN_INTERVAL_SECONDS = int(os.environ.get("SCAN_INTERVAL_SECONDS", "900"))

# Freelancer.com gets its own (longer) interval: unlike Useme's page 1, every
# scan there needs a full headless-browser render (see scraper/freelancer_scraper.py),
# and the site has anti-bot infrastructure (captcha present in its JS bundle) that
# frequent automated visits are more likely to trip -- start conservative.
FREELANCER_SCAN_INTERVAL_SECONDS = int(os.environ.get("FREELANCER_SCAN_INTERVAL_SECONDS", "1200"))

# Freelancehunt.com also sits behind Cloudflare and needs a full headless-browser
# render per scan (see scraper/freelancehunt_scraper.py) -- same conservative
# interval reasoning as Freelancer.com above.
FREELANCEHUNT_SCAN_INTERVAL_SECONDS = int(os.environ.get("FREELANCEHUNT_SCAN_INTERVAL_SECONDS", "1200"))

# Optional Polish residential/ISP proxy, so all traffic to Useme (scraping and
# offer submission) matches the country the account was verified in, rather
# than the VPS's own (German) IP. All requests must go through the same proxy
# consistently -- a mix of proxied and direct requests would be more
# suspicious than no proxy at all.
PROXY_HOST = os.environ.get("PROXY_HOST")
PROXY_PORT = os.environ.get("PROXY_PORT")
PROXY_USERNAME = os.environ.get("PROXY_USERNAME")
PROXY_PASSWORD = os.environ.get("PROXY_PASSWORD")


def proxy_url() -> str | None:
    """"http://user:pass@host:port", or None if no proxy is configured."""
    if not PROXY_HOST:
        return None
    auth = f"{PROXY_USERNAME}:{PROXY_PASSWORD}@" if PROXY_USERNAME else ""
    return f"http://{auth}{PROXY_HOST}:{PROXY_PORT}"


def playwright_proxy() -> dict | None:
    """Playwright wants host/user/pass as separate fields, not one URL."""
    if not PROXY_HOST:
        return None
    proxy = {"server": f"http://{PROXY_HOST}:{PROXY_PORT}"}
    if PROXY_USERNAME:
        proxy["username"] = PROXY_USERNAME
        proxy["password"] = PROXY_PASSWORD
    return proxy
