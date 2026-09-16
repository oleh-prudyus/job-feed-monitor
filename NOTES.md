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

## Remaining
- [ ] `submitter/useme_submitter.py::submit_offer()` — TODO, пише Олег
- [ ] `scripts/save_session.py` — прогнати локально, отримати `storage_state.json`
- [ ] Задеплоїти на VPS 157.90.248.102 (окремий stack поруч з immigration-case-manager, порти не займає)
- [ ] Перший реальний тест: одна вакансія від сканування до відправки офера
- [ ] (опційно, пізніше) Freelancer.com як другий майданчик
