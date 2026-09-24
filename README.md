# useme_bot

Моніторить публічну стрічку вакансій на useme.com, оцінює кожну нову вакансію
LLM-ом за особистими критеріями відсіву, і надсилає збіги в Telegram з
чернеткою офера. Після схвалення (кнопкою в Telegram) бот сам заповнює й
надсилає офер на Useme, використовуючи заздалегідь збережену сесію логіну.

## Компоненти

```
scraper/useme_scraper.py     Парсинг публічних стрічок /pl/jobs/ + /en/jobs/ (requests + BeautifulSoup)
evaluator/llm_evaluator.py   Оцінка вакансії + чернетка офера через Claude/OpenAI
evaluator/criteria.py        Критерії відсіву/прийняття (окремо від промпту)
db/state.py                  SQLite: які вакансії вже бачені/оброблені
bot/telegram_bot.py          Сповіщення + кнопки Схвалити/Редагувати/Відхилити
submitter/useme_submitter.py Заповнення й відправка форми офера (Playwright)
scripts/save_session.py      Одноразовий ручний логін -> storage_state.json
```

## Швидкий старт

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# заповни TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, ANTHROPIC_API_KEY або OPENAI_API_KEY

python3 scripts/save_session.py   # локально, з реальним браузером — один раз
# скопіюй storage_state.json на сервер, у папку бота
```

## Деплой на VPS (Docker)

```bash
# на сервері, поруч з іншими проєктами
git clone <repo> useme_bot && cd useme_bot
cp .env.example .env && nano .env   # заповни токени/ключі
chmod 600 .env

# storage_state.json генерується локально (scripts/save_session.py)
# і копіюється сюди окремо (scp), в git НЕ комітиться

docker compose up -d --build
docker compose logs -f
```

Бот не займає жодного порту (Telegram-бот працює через вихідне long polling),
тож не конфліктує з Caddy чи іншими сервісами на сервері.

## Checklist

- [x] Парсинг публічної стрічки вакансій Useme
- [x] Сканування польської стрічки поряд з англійською (раніше бот бачив лише 5 англомовних вакансій)
- [x] Без ліміту конкуруючих пропозицій для Useme (є виконані замовлення — конкуренція з новачками більше не блокер)
- [x] LLM-оцінка вакансій за критеріями відсіву + чернетка офера
- [x] Telegram-сповіщення з кнопками Схвалити/Редагувати/Відхилити
- [x] Автоматичне заповнення й надсилання офера (Playwright)
- [x] Команда `/status` — стан бота й статистика сканувань
- [x] Деплой на VPS (Docker), персистентна БД
- [ ] Перший реальний тест підтвердження офера на живій вакансії
- [ ] Freelancer.com як другий майданчик (опційно)

## Чому без автологіну

`/en/login/` на Useme захищений Cloudflare-перевіркою на бот-трафік.
Замість того, щоб намагатись її обходити, бот перевикористовує сесію, яку ти
створюєш вручну (`scripts/save_session.py`). Коли сесія протухає — бот
повідомляє в Telegram, і ти повторюєш цей крок.
