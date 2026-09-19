"""Scores a job listing against Oleh's criteria and drafts a short offer
message when it's a good fit. Same provider-detection pattern as hp_translate:
whichever key is set (ANTHROPIC_API_KEY or OPENAI_API_KEY) decides the backend.
"""
import json
import os
from dataclasses import dataclass

from evaluator.criteria import ACCEPT_SIGNALS, REJECT_RULES, SKILLS

SYSTEM_PROMPT = f"""You are helping a beginner freelancer (Oleh, based in Poland) triage
job listings from useme.com and freelancehunt.com (see the "Platform" field in each listing --
they have different typical competition levels, see the rules below). Decide if a
listing is worth applying to, and if so, draft a short cover message he can send as-is or
lightly edit.

His skills:
{SKILLS}

Reject a listing if any of these apply:
{REJECT_RULES}

Good signals:
{ACCEPT_SIGNALS}

Respond ONLY with a JSON object, no other text:
{{
  "is_match": true/false,
  "reason": "one sentence in Ukrainian explaining the verdict",
  "draft_offer": "short offer message written in the exact language named by the 'Listing language' field below, or empty string if is_match is false"
}}

The draft_offer should be 3-5 sentences: reference something specific from the listing,
state what he'd deliver, mention he's building his review history so pricing is fair,
and offer to start quickly. No generic filler."""


@dataclass
class Evaluation:
    is_match: bool
    reason: str
    draft_offer: str


def detect_provider() -> str | None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    elif os.environ.get("OPENAI_API_KEY"):
        return "openai"
    else:
        return None


def _platform_name(job) -> str:
    if "freelancehunt.com" in job.url:
        return "Freelancehunt"
    if "freelancer.com" in job.url:
        return "Freelancer.com"
    return "Useme"


# ISO 639-1 -> readable name for the languages actually seen on Useme/Freelancehunt listings.
# langdetect returns other codes too, but this covers what's come up in practice.
_LANGUAGE_NAMES = {
    "en": "English", "pl": "Polish", "uk": "Ukrainian", "ru": "Russian",
    "pt": "Portuguese", "es": "Spanish", "de": "German", "fr": "French",
    "it": "Italian", "cs": "Czech", "sk": "Slovak", "nl": "Dutch",
    "tr": "Turkish", "ro": "Romanian", "sv": "Swedish", "da": "Danish",
}


def _detect_listing_language(job) -> str:
    # Asking the model to infer the listing's language *and* reliably reply in it
    # was not reliably honored in practice (confirmed live: a Portuguese Freelancer
    # listing got a Ukrainian draft_offer back). Detecting it in code and naming it
    # explicitly removes that guesswork -- same pattern as main.py's competition caps.
    from langdetect import LangDetectException, detect

    text = job.description or job.title
    try:
        code = detect(text)
    except LangDetectException:
        return "the same language as the listing"
    return _LANGUAGE_NAMES.get(code, "the same language as the listing")


def _job_summary(job) -> str:
    return (
        f"Platform: {_platform_name(job)}\n"
        f"Listing language: {_detect_listing_language(job)}\n"
        f"Title: {job.title}\n"
        f"Category: {job.category}\n"
        f"Budget: {job.budget_text}\n"
        f"Offers already submitted: {job.offers_count}\n"
        f"Client: {job.client_name}\n"
        f"Description: {job.description}\n"
        f"URL: {job.url}"
    )


def evaluate(job) -> Evaluation:
    provider = detect_provider()
    if provider is None:
        raise RuntimeError("Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env")

    user_message = _job_summary(job)

    if provider == "anthropic":
        raw = _call_anthropic(user_message)
    else:
        raw = _call_openai(user_message)

    data = json.loads(raw)
    return Evaluation(
        is_match=bool(data.get("is_match")),
        reason=data.get("reason", ""),
        draft_offer=data.get("draft_offer", ""),
    )


def _call_anthropic(user_message: str) -> str:
    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def _call_openai(user_message: str) -> str:
    from openai import OpenAI

    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content
