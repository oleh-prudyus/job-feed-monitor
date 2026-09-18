"""Oleh's vetting criteria, mirrored from Documents/Life/Knowledge/IT/Freelance/Upwork.md
and Useme.md. Kept here (not hardcoded in the prompt string) so it's easy to
tweak without touching the LLM-calling code.
"""

SKILLS = """
- Python: web scraping (Requests/BeautifulSoup, Playwright), pandas, FastAPI, automation, AI API integration (Claude/OpenAI)
- C#/.NET: can build real projects (confirmed skill, not just theory)
- Long-term direction: cybersecurity (security audits, hardening, OSINT) — weight these higher when present
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
- Python-скрапінг/автоматизація/AI-інтеграція/невеликий .NET-застосунок з чітким скоупом
- security audit / hardening для малого бізнесу (найвищий пріоритет)
"""
