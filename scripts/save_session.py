"""Run this LOCALLY (on your own PC, not the VPS) whenever the Useme session
expires. Opens a real, visible browser so you can log in manually — this
deliberately does NOT automate the login itself (Useme's /login/ page sits
behind a Cloudflare challenge that's meant to stop bots, and headless/VPS
automation would just get blocked there anyway).

After you log in and press Enter in the terminal, it saves cookies/local
storage to storage_state.json. Copy that file to the VPS (see README) —
the bot reuses it for everything past login.
"""
from playwright.sync_api import sync_playwright

OUTPUT = "storage_state.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://useme.com/en/login/")

    input("Залогинься в вікні браузера, що відкрилось, тоді натисни Enter тут...")

    page.context.storage_state(path=OUTPUT)
    browser.close()

print(f"Сесію збережено в {OUTPUT}. Скопіюй цей файл на VPS у папку бота.")
