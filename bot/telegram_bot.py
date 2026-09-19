"""Telegram notification + save-for-later flow.

Flow per new matching job:
1. notify_job() sends a card: title, budget, why it matched, draft offer text
   (already in the same language as the listing itself -- see
   evaluator.llm_evaluator.SYSTEM_PROMPT), with two buttons: [Підходить] [Не підходить].
2. Підходить      -> db status "saved". Nothing is sent anywhere automatically --
   Oleh applies himself, on his own time, from /saved.
3. Не підходить   -> db status "rejected", nothing else happens.
4. /saved re-sends a card for every "saved" job with a single [Надіслано] button,
   so he can browse them whenever he has a moment and mark each done as he
   actually submits it manually on the platform.

No auto-submission (Useme's submitter/useme_submitter.py or otherwise) is wired
into this flow -- Oleh explicitly wants to be the one sending every offer himself.
"""
import logging
from datetime import datetime, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from config import FREELANCEHUNT_SCAN_INTERVAL_SECONDS, SCAN_INTERVAL_SECONDS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from db import state

logger = logging.getLogger(__name__)

# status -> (emoji, human label), shown in /status in this order.
_STATUS_LABELS = {
    "notified": ("⏳", "Очікують рішення"),
    "saved": ("💾", "Збережено (чекає надсилання вручну)"),
    "sent": ("📨", "Надіслано вручну"),
    "rejected": ("🙅", "Відхилено вручну"),
    "rejected_auto": ("🤖", "Відхилено автоматично (LLM)"),
    "seen": ("👀", "Побачено, ще не оцінено"),
}


def _time_ago(iso: str) -> str:
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    seconds = int((datetime.now(timezone.utc) - dt).total_seconds())
    if seconds < 60:
        return "щойно"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} хв тому"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} год тому"
    return f"{hours // 24} дн тому"


def _job_card_text(job_row, reason: str | None = None) -> str:
    lines = [
        f"<b>{job_row['title']}</b>",
        job_row["url"],
    ]
    if reason:
        lines.append(f"\n<i>Чому підходить:</i> {reason}")
    lines.append(f"\n<b>Чернетка офера:</b>\n{job_row['draft_offer']}")
    return "\n".join(lines)


def _decision_keyboard(rowid: int) -> InlineKeyboardMarkup:
    # callback_data uses the short sqlite rowid, not job_id -- Telegram caps callback_data
    # at 64 bytes, and Freelancer's job_ids (full URL paths) can exceed that (see
    # state.get_rowid's docstring).
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("👍 Підходить", callback_data=f"save:{rowid}"),
                InlineKeyboardButton("👎 Не підходить", callback_data=f"reject:{rowid}"),
            ]
        ]
    )


def _sent_keyboard(rowid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("✅ Надіслано", callback_data=f"sent:{rowid}")]])


async def notify_job(app: Application, job, evaluation) -> None:
    text = (
        f"<b>{job.title}</b>\n"
        f"{job.budget_text} · {job.category} · {job.offers_count} пропозицій\n"
        f"{job.url}\n\n"
        f"<i>Чому підходить:</i> {evaluation.reason}\n\n"
        f"<b>Чернетка офера:</b>\n{evaluation.draft_offer}"
    )
    await app.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=text,
        parse_mode="HTML",
        reply_markup=_decision_keyboard(state.get_rowid(job.job_id)),
        disable_web_page_preview=True,
    )
    state.set_status(job.job_id, "notified", draft_offer=evaluation.draft_offer, reason=evaluation.reason)


async def _on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    action, rowid_str = query.data.split(":", 1)
    job_id = state.get_job_by_rowid(int(rowid_str))["job_id"]

    # "approve"/"edit" are the old (pre save-for-later) action names -- messages sent
    # before this flow changed still carry buttons with that callback_data, and would
    # otherwise silently do nothing when tapped. Treat them the same as "save" so old
    # pending notifications keep working instead of turning into dead buttons.
    if action in ("save", "approve", "edit"):
        state.set_status(job_id, "saved")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Збережено — знайдеш у /saved, коли будеш готовий надіслати.")

    elif action == "reject":
        state.set_status(job_id, "rejected")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Відхилено.")

    elif action == "sent":
        state.set_status(job_id, "sent")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Позначено як надіслано.")


async def _on_saved(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    jobs = state.jobs_by_status("saved")
    if not jobs:
        await update.message.reply_text("Немає збережених вакансій.")
        return

    for job_row in jobs:
        await update.message.reply_text(
            _job_card_text(job_row, reason=job_row["reason"]),
            parse_mode="HTML",
            reply_markup=_sent_keyboard(job_row["rowid"]),
            disable_web_page_preview=True,
        )


def _scan_lines(label: str, meta_prefix: str, interval_seconds: int) -> list[str]:
    last_scan_at = state.get_meta(f"{meta_prefix}_at")
    last_scan_ok = state.get_meta(f"{meta_prefix}_ok")
    new_count = state.get_meta(f"{meta_prefix}_new_count") or "0"

    lines = [f"<b>{label}</b>"]
    if last_scan_at:
        scan_mark = "🕐" if last_scan_ok != "0" else "❗️"
        lines.append(f"{scan_mark} Останнє сканування: {_time_ago(last_scan_at)}")
        lines.append(f"🆕 Нових вакансій за той прохід: {new_count}")
    else:
        lines.append("🕐 Сканування ще не запускалось")
    lines.append(f"⏭ Наступне — приблизно через {interval_seconds // 60} хв")
    return lines


async def _on_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    started_at = state.get_meta("bot_started_at")
    counts = state.status_counts()
    total = state.total_jobs()

    lines = ["<b>📊 Статус бота</b>", ""]

    lines.append(f"🟢 Працює з: {_time_ago(started_at) if started_at else 'щойно запущено'}")
    lines.append("")
    lines.extend(_scan_lines("Useme", "last_scan", SCAN_INTERVAL_SECONDS))
    lines.append("")
    lines.extend(_scan_lines("Freelancehunt", "freelancehunt_last_scan", FREELANCEHUNT_SCAN_INTERVAL_SECONDS))

    lines.append("")
    lines.append(f"<b>📈 Усього переглянуто вакансій: {total}</b>")
    for status, (emoji, label) in _STATUS_LABELS.items():
        count = counts.get(status, 0)
        if count:
            lines.append(f"{emoji} {label}: {count}")

    await update.message.reply_text("\n".join(lines), parse_mode="HTML", disable_web_page_preview=True)


def build_app() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("status", _on_status))
    app.add_handler(CommandHandler("saved", _on_saved))
    app.add_handler(CallbackQueryHandler(_on_button))
    return app
