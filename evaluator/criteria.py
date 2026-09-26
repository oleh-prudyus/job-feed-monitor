"""Oleh's vetting criteria. Kept here (not hardcoded in the prompt string) so it's easy to
tweak without touching the LLM-calling code.
"""

SKILLS = """
- Python: web scraping (Requests/BeautifulSoup, Playwright), pandas, FastAPI, automation, AI API integration (Claude/OpenAI) -- this is the main focus right now
- C#/.NET: can build real projects (confirmed skill, not just theory)
- NOT ready yet for cybersecurity/security-audit work (still building up university coursework + English) --
  do not treat "security audit / hardening / OSINT" listings as a good fit for now, reject them like any
  other out-of-scope listing even though this is a longer-term direction later
"""

REJECT_RULES = """
NOTE: raw offer-count-too-high is filtered out in code before it ever reaches you
(see main.py's COMPETITION_CAPS -- different platforms have very different typical
bid counts, and a plain numeric threshold in this prompt was not reliably honored
by the model). Judge remaining listings on fit/scope/legitimacy, not bid count.
- lead-gen / harvesting personal contacts (even "verified B2B"; email harvesting from gaming or any other platforms)
- sites with heavy anti-bot protection (LinkedIn and similar) as a key dependency
- vague or oversized scope with no clear boundaries ("various tasks", "long-term equity")
- budget does not match scope (e.g. many records for a tiny budget)
- requires experience Oleh does not have (SAP, ERP, niche enterprise stacks, "US-native only")
- suspected illegal or unethical purpose
- client is clearly already choosing (Interviewing >= 3, Invites sent >= 10)
- spam pattern: the same author posts several near-identical listings in different variations (language, field) with an inflated budget and an empty description
"""

ACCEPT_SIGNALS = """
- one clear site/task -> concrete fields/deliverable -> clear output format
- budget is adequate for the scope
- Python scraping (highest priority right now) / automation / AI integration / a small .NET app with a clear scope
"""
