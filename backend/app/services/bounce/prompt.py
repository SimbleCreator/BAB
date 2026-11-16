"""The messages sent to the model. Pure: takes plain data, returns chat messages."""

import json
from dataclasses import asdict, dataclass, field

DIET_WORDS = {
    "veg": "vegetarian (no meat, no fish, no eggs; dairy is fine)",
    "egg": "vegetarian plus eggs (no meat, no fish)",
    "non_veg": "non-vegetarian (meat, fish, eggs and vegetarian food are all fine)",
}
MODE_WORDS = {
    "activity": (
        "ACTIVITY only: walking, jogging, stretching and no-equipment home exercises "
        "(push-ups, squats, sit-ups, crunches, planks, lunges). Do not include any gym "
        "exercises or machines. Leave gym_focus null, gym_exercises empty, cardio_minutes 0."
    ),
    "gym": (
        "TRAIN only: a gym routine with free weights and machines. Do not add home "
        "exercises, walk_minutes or jog_minutes (keep them empty or 0); gym cardio goes in "
        "cardio_minutes."
    ),
    "both": (
        "BOTH: the user goes to the gym and also walks, jogs or trains at home. Put gym "
        "sessions on gym days and walking, jogging or home exercises on other days. Do not "
        "overload a day with both a hard gym session and a hard home session."
    ),
}

SHAPE = {
    "summary": "2-3 sentences: what this week focuses on and why, addressed to the user",
    "days": [
        {
            "day": "Mon",
            "rest": False,
            "walk_minutes": 30,
            "jog_minutes": 0,
            "steps_target": 8000,
            "home_exercises": [
                {"name": "Push-ups", "sets": 3, "reps": 10, "rest_s": 60, "notes": "knees ok"}
            ],
            "gym_focus": None,
            "gym_exercises": [],
            "cardio_minutes": 0,
            "stretching": [{"name": "Hamstring stretch", "seconds": 30}],
        }
    ],
    "diet": {
        "principles": ["short rule"],
        "eat_more": ["food"],
        "limit": ["food or habit to cut down"],
        "days": [
            {
                "day": "Mon",
                "breakfast": "meal with rough portion",
                "lunch": "...",
                "snack": "...",
                "dinner": "...",
            }
        ],
    },
    "supplements_advice": ["one line per supplement the user takes"],
    "tips": ["3 to 6 short, practical tips for this week"],
}

SYSTEM = f"""You are Bounce, the coach inside the B.A.B fitness app. You write a one-week \
plan for one adult user from the data you are given.

Rules:
- Reply with ONE JSON object only, no prose and no code fences, in exactly this shape:
{json.dumps(SHAPE, indent=1)}
- "days" has 7 entries, Mon to Sun in order, in both "days" and "diet.days".
- Exercise items use "reps" for counted moves or "seconds" for holds, not both.
- Respect the training mode, the diet type, the minutes per session, the days per \
week (other days are rest or light walking) and the user's level. Beginners start easy.
- Prefer common Indian home food (dal, roti, rice, sabzi, curd, paneer, poha, upma, idli, \
dosa, sprouts, fruit) with rough portions. Match the daily calorie and protein targets \
given; do not invent different targets.
- Build the meal plan mainly from the user's "usual_foods" and dishes of their region or \
city when given: keep familiar food and change portions and sides, rather than replacing \
it with unfamiliar "diet" food.
- Fit the user's life when given: wake time (when to train), kind of work (desk jobs get \
short movement breaks; physical work needs less extra cardio), where food comes from \
(hostel or mess: best picks from typical mess food; eating out: sensible orders), the \
daily food budget in rupees (keep each day's meals within it, using affordable \
staples), fasting days and sleep.
- "calendar" lists festivals, fasting periods and seasons in this plan's week, each with a \
tip: adjust the plan to them (fasting-friendly meals and lighter training if the user \
fasts, indoor options in the monsoon, early or late sessions in summer heat).
- Weight loss: daily walking or steps first, then home or gym strength work; never crash diets.
- If check-ins show progress, progress the plan a little; if weight is stuck or rising \
against the goal, adjust gently and say so in the summary.
- Supplements: analyse only the ones the user says they take. Be factual and cautious. \
Never suggest steroids, SARMs, prohormones or fat burners. If the user takes none, \
"supplements_advice" is an empty list.
- If the user notes an injury, avoid loading it and suggest seeing a professional.
- Plain, short, encouraging wording. No quotes from films, games, books or celebrities. \
Do not claim medical certainty."""


@dataclass
class CheckinPoint:
    day: str
    weight_kg: float
    waist_cm: float | None


@dataclass
class GymInfo:
    experience: str
    days_per_week: int
    session_minutes: int
    supplements: list[str]
    supplements_note: str | None
    injuries_note: str | None


@dataclass
class Lifestyle:
    city: str | None = None
    state: str | None = None
    region: str | None = None
    work: str | None = None
    food_from: str | None = None
    wake_time: str | None = None
    usual_foods: list[str] = field(default_factory=list)
    sleep_hours: float | None = None
    sweet_drinks_per_day: int | None = None
    fasting: str | None = None
    food_budget_inr_per_day: int | None = None


@dataclass
class CalendarNote:
    name: str
    kind: str
    tip: str


@dataclass
class BounceContext:
    mode: str
    age: int
    sex: str
    height_cm: float
    weight_kg: float
    goal: str
    level: str
    minutes_per_day: int
    days_per_week: int
    diet_type: str
    daily_step_goal: int
    calories_kcal: int
    protein_g: int
    carbs_g: int
    fat_g: int
    gym: GymInfo | None = None
    life: Lifestyle = field(default_factory=Lifestyle)
    calendar: list[CalendarNote] = field(default_factory=list)
    checkins: list[CheckinPoint] = field(default_factory=list)
    avg_steps_7d: int | None = None
    step_goal_days_7d: int = 0
    workouts_done_7d: int = 0
    previous_summary: str | None = None


def build_messages(ctx: BounceContext, retry_reason: str | None = None) -> list[dict[str, str]]:
    data = asdict(ctx)
    data["diet_type"] = DIET_WORDS.get(ctx.diet_type, ctx.diet_type)
    data["goal"] = ctx.goal.replace("_", " ")
    user = (
        f"Training mode: {MODE_WORDS[ctx.mode]}\n"
        f"Diet: {DIET_WORDS.get(ctx.diet_type, ctx.diet_type)}.\n"
        "User data (kg, cm, minutes; targets come from the app and are fixed):\n"
        f"{json.dumps(data, indent=1)}\n"
        "Write this week's plan as the JSON object."
    )
    # One user message: some open models (Gemma) have no separate system role.
    messages = [{"role": "user", "content": f"{SYSTEM}\n\n{user}"}]
    if retry_reason:
        messages.append({"role": "assistant", "content": "(reply rejected)"})
        messages.append(
            {
                "role": "user",
                "content": f"Your last reply could not be used: {retry_reason}. "
                "Reply again with the corrected JSON object only.",
            }
        )
    return messages
