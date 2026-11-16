"""Pure rules around Bounce: plan state, diet-type checks, mode separation and safety text.
No FastAPI or database imports, so these are unit tested directly."""

import re
from dataclasses import dataclass
from datetime import date

from app.schemas.bounce import PlanContent

PLAN_DAYS = 7
DISCLAIMER = "Estimates only, not medical advice. Check with a doctor before a big change."
SUPPLEMENT_SAFETY = (
    "Supplements are optional. Food comes first, and a doctor or registered dietitian can "
    "tell you whether you need any."
)
FAT_BURNER_WARNING = (
    "Fat burners are not recommended: they often contain high doses of stimulants and do "
    "little that a calorie target and daily steps cannot do."
)
NEVER_SUGGEST = "Bounce never suggests steroids, SARMs, prohormones or fat burners."

# Words that break a diet type. Matched as whole words, so "eggplant" is fine.
MEAT_WORDS = (
    "chicken",
    "mutton",
    "lamb",
    "goat",
    "beef",
    "pork",
    "bacon",
    "ham",
    "sausage",
    "salami",
    "turkey",
    "meat",
    "keema",
    "fish",
    "tuna",
    "salmon",
    "sardine",
    "mackerel",
    "prawn",
    "prawns",
    "shrimp",
    "crab",
    "seafood",
)
EGG_WORDS = ("egg", "eggs", "omelette", "omelet")
_FORBIDDEN = {
    "veg": MEAT_WORDS + EGG_WORDS,
    "egg": MEAT_WORDS,
    "non_veg": (),
}
# A word that follows these is being excluded, not suggested ("no egg", "egg-free").
_NEGATION = re.compile(r"\b(no|without|skip|avoid|instead of)\s+$")


@dataclass(frozen=True)
class PlanFacts:
    created_on: date  # the user's local date when the plan was made
    based_on_checkin_day: date | None
    mode: str


def plan_state(plan: PlanFacts | None, latest_checkin: date | None, today: date) -> str:
    """none -> no plan yet; active -> inside its week; after a week, update_ready if a newer
    check-in exists, otherwise checkin_needed."""
    if plan is None:
        return "none"
    if (today - plan.created_on).days < PLAN_DAYS:
        return "active"
    newer = latest_checkin is not None and (
        plan.based_on_checkin_day is None or latest_checkin > plan.based_on_checkin_day
    )
    return "update_ready" if newer else "checkin_needed"


def _hits(text: str, words: tuple[str, ...]) -> list[str]:
    found = []
    lower = text.lower()
    for w in words:
        for m in re.finditer(rf"\b{re.escape(w)}\b", lower):
            before = lower[max(0, m.start() - 20) : m.start()]
            after = lower[m.end() : m.end() + 6]
            if _NEGATION.search(before) or after.startswith("-free"):
                continue
            found.append(w)
            break
    return found


def diet_violations(content: PlanContent, diet_type: str) -> list[str]:
    """Foods in the meal plan or the 'eat more' list that the user's diet type excludes."""
    words = _FORBIDDEN.get(diet_type, ())
    if not words:
        return []
    texts = list(content.diet.eat_more)
    for d in content.diet.days:
        texts += [d.breakfast, d.lunch, d.snack, d.dinner]
    found: list[str] = []
    for t in texts:
        for w in _hits(t, words):
            if w not in found:
                found.append(w)
    return found


def enforce_mode(content: PlanContent, mode: str) -> PlanContent:
    """Keep Activity and Train apart unless the user does both."""
    days = []
    for d in content.days:
        d = d.model_copy()
        if mode == "activity":
            d.gym_focus, d.gym_exercises, d.cardio_minutes = None, [], 0
        elif mode == "gym":
            d.home_exercises, d.walk_minutes, d.jog_minutes = [], 0, 0
        if d.rest:
            d.home_exercises, d.gym_exercises, d.gym_focus = [], [], None
            d.jog_minutes, d.cardio_minutes = 0, 0
        days.append(d)
    return content.model_copy(update={"days": days})


def supplement_advice(model_advice: list[str], supplements: list[str], mode: str) -> list[str]:
    """Bounce's notes on supplements, with fixed safety lines the model cannot drop."""
    if mode == "activity" and not supplements:
        return []
    advice = [a for a in model_advice if not _mentions_banned(a)][:4]
    if "fat_burner" in supplements:
        advice.insert(0, FAT_BURNER_WARNING)
    advice += [SUPPLEMENT_SAFETY, NEVER_SUGGEST]
    return advice


_BANNED = re.compile(r"\b(steroids?|sarms?|prohormones?|anabolic|clenbuterol|dnp)\b", re.I)


def _mentions_banned(text: str) -> bool:
    """Drop any model line that names a banned substance, whatever it says about it."""
    return bool(_BANNED.search(text))


def finalize(content: PlanContent, mode: str, supplements: list[str]) -> PlanContent:
    content = enforce_mode(content, mode)
    tips = [t for t in content.tips if not _mentions_banned(t)] or [
        "Small steps every day beat a perfect plan once a week."
    ]
    return content.model_copy(
        update={
            "tips": tips,
            "supplements_advice": supplement_advice(content.supplements_advice, supplements, mode),
        }
    )


# Notifications ------------------------------------------------------------------------
# Bounce "jumps out with a letter" for one of these, most important first. Hours are the
# user's local time; a meal is asked about once its hour has passed and it is not logged.
MEAL_NUDGE_HOURS: tuple[tuple[str, int], ...] = (
    ("breakfast", 10),
    ("lunch", 15),
    ("snack", 18),
    ("dinner", 21),
)
ACTIVITY_NUDGE_HOUR = 12  # no numbers for today yet
STEPS_NUDGE_HOUR = 18  # numbers logged but under the step goal


@dataclass(frozen=True)
class Nudge:
    id: str  # stable per day and reason, so the app can remember it was dismissed
    kind: str  # easy | checkin | meals | activity
    title: str
    message: str
    action_label: str


def pick_nudge(
    day: date,
    hour: int,
    checkin_due: bool,
    meals_logged: set[str],
    steps: int | None,
    step_goal: int,
    offer_easy_day: bool = False,
) -> Nudge | None:
    """At most one notification, most important first. A user who has gone quiet for a
    few days is offered an easy day before anything else, so coming back feels small."""
    if offer_easy_day:
        return Nudge(
            f"easy:{day}",
            "easy",
            "Rough few days?",
            "Take an easy day: 10 minutes keeps your streak alive. Small steps still count.",
            "Easy day",
        )
    if checkin_due:
        return Nudge(
            f"checkin:{day}",
            "checkin",
            "Weekly check-in",
            "Time to weigh in. Your check-in is what lets your plan adapt to you.",
            "Check in",
        )
    missed = [m for m, h in MEAL_NUDGE_HOURS if hour >= h and m not in meals_logged]
    if missed:
        meal = missed[-1]
        return Nudge(
            f"meals:{day}:{meal}",
            "meals",
            "What did you eat?",
            f"What did you have for {'your snack' if meal == 'snack' else meal}? "
            "Log it so your food stays on track.",
            "Log food",
        )
    if steps is None and hour >= ACTIVITY_NUDGE_HOUR:
        return Nudge(
            f"activity:{day}",
            "activity",
            "Today's check-up",
            "How is today going? Add your steps from your watch or phone.",
            "Add numbers",
        )
    if steps is not None and steps < step_goal and hour >= STEPS_NUDGE_HOUR:
        return Nudge(
            f"steps:{day}",
            "activity",
            "Today's check-up",
            f"{step_goal - steps:,} steps to your goal today. An evening walk closes the gap.",
            "See activity",
        )
    return None
