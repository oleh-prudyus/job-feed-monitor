"""Telegram notification + approval flow.

Flow per new matching job:
1. notify_job() sends a card: title, budget, why it matched, draft offer text,
   with [Approve] [Edit] [Reject] buttons.
2. Approve  -> db status "approved", submitter.submit_offer() is triggered.
3. Reject   -> db status "rejected", nothing else happens.
4. Edit     -> bot asks for replacement text; next plain-text message from
   Oleh becomes the new draft_offer and is treated as an approval.
"""
import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from db import state

logger = logging.getLogger(__name__)

# job_id of the listing currently awaiting replacement text via /edit, if any.
_awaiting_edit: str | None = None


def _keyboard(job_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Схвалити", callback_data=f"approve:{job_id}"),
                InlineKeyboardButton("✏️ Редагувати", callback_data=f"edit:{job_id}"),
                InlineKeyboardButton("❌ Відхилити", callback_data=f"reject:{job_id}"),
            ]
        ]
    )


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
        reply_markup=_keyboard(job.job_id),
        disable_web_page_preview=True,
    )
    state.set_status(job.job_id, "notified", draft_offer=evaluation.draft_offer)


async def _on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global _awaiting_edit
    query = update.callback_query
    await query.answer()
    action, job_id = query.data.split(":", 1)

    if action == "approve":
        job = state.get_job(job_id)
        state.set_status(job_id, "approved")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Схвалено — надсилаю офер на Useme.")
        from submitter.useme_submitter import submit_offer

        try:
            await asyncio.to_thread(submit_offer, job_id, job["url"], job["draft_offer"])
            state.set_status(job_id, "sent")
            await query.message.reply_text("Офер надіслано.")
        except Exception as exc:  # submission is best-effort; never crash the bot
            state.set_status(job_id, "failed")
            logger.exception("Failed to submit offer for %s", job_id)
            await query.message.reply_text(f"Не вдалося надіслати офер: {exc}")

    elif action == "reject":
        state.set_status(job_id, "rejected")
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Відхилено.")

    elif action == "edit":
        _awaiting_edit = job_id
        await query.message.reply_text(
            "Надішли текст офера, яким замінити чернетку — наступне твоє повідомлення."
        )


async def _on_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global _awaiting_edit
    if _awaiting_edit is None:
        return

    job_id = _awaiting_edit
    _awaiting_edit = None
    new_text = update.message.text
    state.set_status(job_id, "approved", draft_offer=new_text)

    job = state.get_job(job_id)
    await update.message.reply_text("Замінено — надсилаю офер на Useme.")
    from submitter.useme_submitter import submit_offer

    try:
        await asyncio.to_thread(submit_offer, job_id, job["url"], new_text)
        state.set_status(job_id, "sent")
        await update.message.reply_text("Офер надіслано.")
    except Exception as exc:
        state.set_status(job_id, "failed")
        logger.exception("Failed to submit offer for %s", job_id)
        await update.message.reply_text(f"Не вдалося надіслати офер: {exc}")


def build_app() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(_on_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _on_edit_text))
    return app
