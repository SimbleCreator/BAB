"""Then-vs-now progress cards, one every CARD_DAYS days from the first check-in.

Each card compares the first check-in ("then") with the latest check-in up to the card's
last day ("now"), sums up the card's 4-week block (steps, workouts, runs, days with meals)
next to the block before it, and picks a few short highlights worth celebrating.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

CARD_DAYS = 28
MAX_CARDS = 12
MAX_HIGHLIGHTS = 4
MEASURES = ("weight_kg", "waist_cm", "chest_cm", "arms_cm", "thighs_cm")
WINS = ("energy", "sleep", "stairs")
# Smallest changes worth calling out.
MIN_KG = 0.3
MIN_CM = 0.5
MIN_STEP_RISE = 500
STAY_FIT_BAND_KG = 1.0
WIN_WORDS = {
    "energy": "Energy",
    "sleep": "Sleep",
    "stairs": "Stairs without getting out of breath",
}


@dataclass(frozen=True)
class CheckinPoint:
    day: date
    weight_kg: float
    waist_cm: float | None = None
    chest_cm: float | None = None
    arms_cm: float | None = None
    thighs_cm: float | None = None
    energy: int | None = None
    sleep: int | None = None
    stairs: int | None = None


@dataclass(frozen=True)
class DailyLog:
    """Everything the cards need from the user's daily records."""

    steps: dict[date, int] = field(default_factory=dict)
    workout_days: frozenset[date] = frozenset()
    run_m: dict[date, int] = field(default_factory=dict)
    meal_days: frozenset[date] = frozenset()


@dataclass(frozen=True)
class Change:
    name: str
    then: float
    now: float
    change: float


@dataclass(frozen=True)
class Block:
    start: date
    end: date
    avg_steps: int | None  # over days with a step count
    workouts: int
    run_km: float
    meal_days: int


@dataclass(frozen=True)
class Card:
    number: int
    start: date
    end: date
    then_day: date
    now_day: date
    measures: list[Change]
    wins: list[Change]
    block: Block
    previous_block: Block | None
    highlights: list[str]


def cards_ready(first_day: date, today: date) -> int:
    """How many cards are ready: card n is ready once its CARD_DAYS days are over."""
    return max(0, (today - first_day).days // CARD_DAYS)


def next_card_on(first_day: date, today: date) -> date:
    return first_day + timedelta(days=CARD_DAYS * (cards_ready(first_day, today) + 1))


def block(log: DailyLog, start: date, end: date) -> Block:
    def inside(d: date) -> bool:
        return start <= d <= end

    steps = [s for d, s in log.steps.items() if inside(d)]
    return Block(
        start=start,
        end=end,
        avg_steps=round(sum(steps) / len(steps)) if steps else None,
        workouts=sum(1 for d in log.workout_days if inside(d)),
        run_km=round(sum(m for d, m in log.run_m.items() if inside(d)) / 1000, 1),
        meal_days=sum(1 for d in log.meal_days if inside(d)),
    )


def _changes(points: list[CheckinPoint], names: tuple[str, ...]) -> list[Change]:
    """First known value against the latest known value, for each name."""
    out = []
    for name in names:
        known = [getattr(p, name) for p in points if getattr(p, name) is not None]
        if len(known) >= 2:
            then, now = float(known[0]), float(known[-1])
            out.append(Change(name, then, now, round(now - then, 1)))
    return out


def _weight_line(goal: str, change: float) -> str | None:
    kg = abs(change)
    if goal == "lose_fat" and change <= -MIN_KG:
        return f"{kg:g} kg down since you started."
    if goal == "build_muscle" and change >= MIN_KG:
        return f"{kg:g} kg up since you started."
    if goal == "stay_fit" and kg <= STAY_FIT_BAND_KG:
        return "Your weight is holding steady, right where you want it."
    return None


def highlights(
    goal: str, measures: list[Change], wins: list[Change], blk: Block, prev: Block | None
) -> list[str]:
    lines: list[str] = []
    by_name = {c.name: c for c in measures}
    if "weight_kg" in by_name and (line := _weight_line(goal, by_name["weight_kg"].change)):
        lines.append(line)
    waist = by_name.get("waist_cm")
    if waist and waist.change <= -MIN_CM:
        lines.append(f"Waist {abs(waist.change):g} cm smaller.")
    for w in wins:
        if w.change > 0:
            lines.append(f"{WIN_WORDS[w.name]}: up from {w.then:g} to {w.now:g} out of 5.")
    if blk.avg_steps is not None and prev is not None and prev.avg_steps is not None:
        rise = blk.avg_steps - prev.avg_steps
        if rise >= MIN_STEP_RISE:
            lines.append(f"{rise:,} more steps a day than the 4 weeks before.")
    if blk.workouts:
        lines.append(f"{blk.workouts} workout{'s' if blk.workouts != 1 else ''} done in 4 weeks.")
    if blk.run_km:
        lines.append(f"{blk.run_km:g} km run in 4 weeks.")
    if not lines:
        lines.append("Four more weeks on the board. Showing up is the hard part, and you did.")
    return lines[:MAX_HIGHLIGHTS]


def build_cards(goal: str, checkins: list[CheckinPoint], log: DailyLog, today: date) -> list[Card]:
    """Ready cards, newest first (at most MAX_CARDS)."""
    pts = sorted(checkins, key=lambda c: c.day)
    if not pts:
        return []
    first = pts[0].day
    ready = cards_ready(first, today)
    out = []
    for n in range(max(1, ready - MAX_CARDS + 1), ready + 1):
        start = first + timedelta(days=CARD_DAYS * (n - 1))
        end = start + timedelta(days=CARD_DAYS - 1)
        upto = [p for p in pts if p.day <= end]
        blk = block(log, start, end)
        prev = block(log, start - timedelta(days=CARD_DAYS), start - timedelta(days=1))
        prev_block = prev if n > 1 else None
        measures = _changes(upto, MEASURES)
        wins = _changes(upto, WINS)
        out.append(
            Card(
                number=n,
                start=start,
                end=end,
                then_day=first,
                now_day=upto[-1].day,
                measures=measures,
                wins=wins,
                block=blk,
                previous_block=prev_block,
                highlights=highlights(goal, measures, wins, blk, prev_block),
            )
        )
    return list(reversed(out))
