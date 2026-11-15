import json

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def plan_dict(meal: str = "Poha with peanuts and curd", **over) -> dict:
    days = []
    for i, d in enumerate(DAYS):
        rest = i in (2, 6)
        days.append(
            {
                "day": d,
                "rest": rest,
                "walk_minutes": 30,
                "jog_minutes": 0 if rest else 10,
                "steps_target": 8000,
                "home_exercises": []
                if rest
                else [{"name": "Push-ups", "sets": 3, "reps": 10, "rest_s": 60}],
                "gym_focus": None if rest else "Upper body",
                "gym_exercises": []
                if rest
                else [{"name": "Bench press", "sets": 3, "reps": 8, "rest_s": 90}],
                "cardio_minutes": 0 if rest else 10,
                "stretching": [{"name": "Hamstring stretch", "seconds": 30}],
            }
        )
    plan = {
        "summary": "A gentle first week built around daily walks.",
        "days": days,
        "diet": {
            "principles": ["Protein in every meal"],
            "eat_more": ["Dal", "Sprouts"],
            "limit": ["Sugary drinks"],
            "days": [
                {
                    "day": d,
                    "breakfast": meal,
                    "lunch": "Dal, roti, sabzi",
                    "snack": "Fruit",
                    "dinner": "Paneer bhurji with roti",
                }
                for d in DAYS
            ],
        },
        "supplements_advice": ["Creatine is well studied at 3-5 g a day."],
        "tips": ["Walk after dinner.", "Take steroids for faster gains."],
    }
    plan.update(over)
    return plan


class FakeLLM:
    model = "fake/model"
    last_model = None

    def __init__(self, *replies: str) -> None:
        self.replies = list(replies)
        self.calls: list[list[dict]] = []

    async def complete(self, messages, max_tokens):
        self.calls.append(messages)
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, Exception):
            raise reply
        return reply


def reply(plan: dict | None = None) -> str:
    return "Here you go:\n```json\n" + json.dumps(plan or plan_dict()) + "\n```"
