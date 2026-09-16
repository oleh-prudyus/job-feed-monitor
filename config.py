import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])

USEME_EMAIL = os.environ.get("USEME_EMAIL")
USEME_PASSWORD = os.environ.get("USEME_PASSWORD")

# How often to re-scan the feed, in seconds.
SCAN_INTERVAL_SECONDS = int(os.environ.get("SCAN_INTERVAL_SECONDS", "900"))
