"""Festival and season calendar: which events are on for a day and a region."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

Kind = Literal["festival", "fasting", "season"]
KINDS = ("festival", "fasting", "season")


@dataclass(frozen=True)
class Event:
    code: str
    name: str
    kind: Kind
    recurring: bool
    start: str  # "MM-DD" when recurring, else "YYYY-MM-DD"
    end: str
    regions: tuple[str, ...]
    tip: str


def _md(s: str) -> tuple[int, int]:
    m, d = s.split("-")
    return int(m), int(d)


def is_on(event: Event, day: date) -> bool:
    if not event.recurring:
        return date.fromisoformat(event.start) <= day <= date.fromisoformat(event.end)
    start, end, here = _md(event.start), _md(event.end), (day.month, day.day)
    if start <= end:
        return start <= here <= end
    return here >= start or here <= end  # wraps over the new year


def applies(event: Event, region: str | None) -> bool:
    """Events with no regions apply everywhere; regional ones only to that region."""
    return not event.regions or (region is not None and region in event.regions)


def events_on(events: tuple[Event, ...], day: date, region: str | None) -> list[Event]:
    """Events on a day for a region: festivals and fasting first, then seasons."""
    hits = [e for e in events if is_on(e, day) and applies(e, region)]
    return sorted(hits, key=lambda e: (KINDS.index(e.kind), e.code))


def events_between(
    events: tuple[Event, ...], start: date, days: int, region: str | None
) -> list[Event]:
    """Events on any day from `start` for `days` days, each once, in calendar order."""
    seen: dict[str, Event] = {}
    for i in range(days):
        for e in events_on(events, start + timedelta(days=i), region):
            seen.setdefault(e.code, e)
    return list(seen.values())
