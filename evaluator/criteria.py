"""Oleh's vetting criteria, mirrored from Documents/Life/Knowledge/IT/Freelance/Upwork.md
and Useme.md. Kept here (not hardcoded in the prompt string) so it's easy to
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
- lead-gen / збір персональних контактів (навіть "verified B2B", email harvesting з ігрових/будь-яких платформ)
- сайти з важким anti-bot захистом (LinkedIn і подібні) як ключова залежність
- розмитий/завеликий обсяг без чітких меж ("various tasks", "long-term equity")
- невідповідність бюджету і обсягу (напр. багато записів за мізерний бюджет)
- вимога досвіду, якого немає (SAP, ERP, вузькі enterprise-стеки, "US-native only")
- підозра на нелегальну/неетичну мету
- клієнт явно вже вибирає (Interviewing >= 3, Invites sent >= 10)
- спам-патерн: той самий автор постить кілька майже ідентичних вакансій різними варіаціями (мова, поле) з завищеним бюджетом за нульовим описом
"""

ACCEPT_SIGNALS = """
- один чіткий сайт/задача → конкретні поля/deliverable → зрозумілий формат виводу
- бюджет adекватний обсягу
- Python-скрапінг (найвищий пріоритет зараз) / автоматизація / AI-інтеграція / невеликий .NET-застосунок з чітким скоупом
"""
