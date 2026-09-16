"""Converts a Cookie-Editor browser extension JSON export into the
storage_state.json format Playwright expects (context.storage_state()).

Usage:
    python3 scripts/cookies_to_storage_state.py cookies_export.json storage_state.json

Why this exists: a cookie-editor extension can read httpOnly cookies (like
Useme's sessionid) via the browser's cookie API, which plain page JavaScript
cannot. That makes it a simpler alternative to scripts/save_session.py for
grabbing a session — export cookies for useme.com from the extension, run
this converter, copy the result to the bot's storage_state.json.
"""
import json
import sys

SAME_SITE_MAP = {
    "lax": "Lax",
    "strict": "Strict",
    "no_restriction": "None",
    "unspecified": "Lax",  # Playwright has no "unspecified"; Lax is the safe default
    "none": "None",
}


def convert(cookies: list[dict]) -> dict:
    playwright_cookies = []
    for c in cookies:
        expires = -1.0 if c.get("session") else float(c["expirationDate"])
        playwright_cookies.append(
            {
                "name": c["name"],
                "value": c["value"],
                "domain": c["domain"],
                "path": c["path"],
                "expires": expires,
                "httpOnly": c["httpOnly"],
                "secure": c["secure"],
                "sameSite": SAME_SITE_MAP.get((c.get("sameSite") or "").lower(), "Lax"),
            }
        )
    return {"cookies": playwright_cookies, "origins": []}


if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    with open(src) as f:
        cookies = json.load(f)
    with open(dst, "w") as f:
        json.dump(convert(cookies), f, indent=2)
    print(f"Wrote {dst} ({len(cookies)} cookies)")
