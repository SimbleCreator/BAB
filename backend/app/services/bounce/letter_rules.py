"""Rules for the letter from future you. Pure Python, no database or network.

The model writes only the body. The greeting (with the user's name) and the sign-off are
added by the server, so the name is never sent to the AI service. Sentences that promise
results, name a weight, or mention banned substances or cures are removed.
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

LETTER_DAYS = 90
MIN_PARAGRAPHS = 2
MAX_PARAGRAPHS = 4
MIN_WORDS = 60
MAX_WORDS = 260
MAX_PARAGRAPH_CHARS = 900

State = Literal["none", "sealed", "ready", "opened"]

_SENTENCE = re.compile(r"(?<=[.!?])\s+")
# A weight or size number ("5 kg", "3.5 kilos", "10 pounds", "4 inches", "3 cm").
_BODY_NUMBER = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:kg|kgs|kilo|kilos|kilograms?|lbs?|pounds?|cm|inch(?:es)?)\b", re.I
)
_PROMISE = re.compile(
    r"\b(guarantee[ds]?|promise[ds]?|definitely|for sure|100\s*%|certainly will|"
    r"cured?|diagnos\w*|miracle|overnight)\b",
    re.I,
)
_BANNED = re.compile(
    r"\b(steroids?|sarms?|prohormones?|anabolic|clenbuterol|dnp|fat burners?)\b", re.I
)


def open_on(written_on: date) -> date:
    return written_on + timedelta(days=LETTER_DAYS)


def state(written_on: date | None, opened: bool, today: date) -> State:
    if written_on is None:
        return "none"
    if opened:
        return "opened"
    return "ready" if today >= open_on(written_on) else "sealed"


def _safe(sentence: str) -> bool:
    return not (
        _BODY_NUMBER.search(sentence) or _PROMISE.search(sentence) or _BANNED.search(sentence)
    )


def clean(paragraphs: list[str]) -> list[str]:
    """Drop unsafe sentences, then empty paragraphs; keep at most MAX_PARAGRAPHS."""
    out = []
    for p in paragraphs:
        kept = [s for s in _SENTENCE.split(p.strip()) if s and _safe(s)]
        text = " ".join(kept).strip()
        if text:
            out.append(text[:MAX_PARAGRAPH_CHARS])
    return out[:MAX_PARAGRAPHS]


def problem(paragraphs: list[str]) -> str | None:
    """Why a cleaned letter cannot be used, or None when it is fine."""
    words = sum(len(p.split()) for p in paragraphs)
    if len(paragraphs) < MIN_PARAGRAPHS:
        return f"it needs {MIN_PARAGRAPHS} to {MAX_PARAGRAPHS} paragraphs"
    if words < MIN_WORDS:
        return f"it is too short ({words} words; write {MIN_WORDS} to {MAX_WORDS})"
    if words > MAX_WORDS * 1.5:
        return f"it is too long ({words} words; write {MIN_WORDS} to {MAX_WORDS})"
    return None


@dataclass(frozen=True)
class Snapshot:
    """The user's numbers on a day, for the then-vs-now view when the letter opens."""

    weight_kg: float
    target_weight_kg: float | None
    waist_cm: float | None
    avg_steps_7d: int | None
    workouts_28d: int
    meal_days_28d: int
    step_goal: int
