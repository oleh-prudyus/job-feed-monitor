# Working notes — status & remaining tasks

Internal tracker, not part of the public README.

## Done
- [x] Скрапер Useme feed (`scraper/useme_scraper.py`), перевірено на реальній сторінці
- [x] SQLite стан (`db/state.py`)
- [x] LLM-оцінювач + критерії (`evaluator/`)
- [x] Telegram-бот: сповіщення + кнопки Схвалити/Редагувати/Відхилити (`bot/telegram_bot.py`)
- [x] Дизайн-рішення: без автологіну (Cloudflare на /login/) — ручна сесія через `scripts/save_session.py`
- [x] Форма офера на Useme розібрана (селектори полів задокументовані в submitter TODO)

- [x] `main.py` — оркестрація: job_queue python-telegram-bot (без окремого APScheduler) + запуск бота
- [x] Docker-образ (`docker/Dockerfile`, base з preinstalled Chromium) + `docker-compose.yml`

- [x] `submitter/useme_submitter.py::submit_offer()` — реалізовано (Playwright, .type() для contenteditable-редактора)
- [x] Сесія отримана через експорт кукі з браузерного плагіна (простіше за `save_session.py`) + конвертер `scripts/cookies_to_storage_state.py`
- [x] Задеплоєно на VPS 157.90.248.102 (`~/useme_bot`, окремий stack, порти не займає) — контейнер живий, сканує кожні 15 хв, БД персистить між рестартами

## Remaining
- [ ] Перший реальний тест: підтвердити офер через Telegram-кнопку "Схвалити" на живій вакансії — перевірити, чи `submit_offer()` і кнопка Summary-кроку (селектор не підтверджено наосліп, дивись коментар у коді) справді працюють
- [ ] Коли сесія (кукі) протухне — повторити експорт з плагіна й прогнати `cookies_to_storage_state.py` заново
- [ ] (опційно, пізніше) Freelancer.com як другий майданчик
