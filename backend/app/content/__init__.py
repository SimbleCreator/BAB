"""Built-in content loaded from JSON files in this folder."""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.engines.training_engine import Drill, Exercise

CONTENT_DIR = Path(__file__).resolve().parent
GROUPS = ("push", "pull", "legs", "core", "cardio")


def _read(name: str) -> dict:
    with (CONTENT_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def motivational_lines() -> tuple[str, ...]:
    lines = _read("lines.json")["lines"]
    if not lines or not all(isinstance(x, str) and x.strip() for x in lines):
        raise ValueError("lines.json must hold a non-empty list of strings")
    return tuple(lines)


@dataclass(frozen=True)
class ExerciseLibrary:
    exercises: tuple[Exercise, ...]
    warmup: tuple[Drill, ...]
    cooldown: tuple[Drill, ...]

    def by_code(self) -> dict[str, Exercise]:
        return {e.code: e for e in self.exercises}

    def drill(self, code: str) -> Drill | None:
        return next((d for d in (*self.warmup, *self.cooldown) if d.code == code), None)


@lru_cache
def exercise_library() -> ExerciseLibrary:
    raw = _read("exercises.json")
    exercises = tuple(Exercise(**e) for e in raw["exercises"])
    codes = [e.code for e in exercises]
    if len(codes) != len(set(codes)):
        raise ValueError("exercises.json: duplicate codes")
    known = set(codes)
    for e in exercises:
        if e.group not in GROUPS or e.type not in ("reps", "timed"):
            raise ValueError(f"exercises.json: bad group or type for {e.code}")
        if not 1 <= e.difficulty <= 5:
            raise ValueError(f"exercises.json: difficulty out of range for {e.code}")
        for ref in (e.easier, e.harder):
            if ref is not None and ref not in known:
                raise ValueError(f"exercises.json: {e.code} points to unknown {ref}")
    for g in GROUPS:
        if not any(e.group == g and not e.needs_bar for e in exercises):
            raise ValueError(f"exercises.json: group {g} needs exercises without a bar")
    return ExerciseLibrary(
        exercises,
        tuple(Drill(**d) for d in raw["warmup"]),
        tuple(Drill(**d) for d in raw["cooldown"]),
    )


def load_all() -> None:
    """Load and validate every content file. Called at startup so bad content fails fast."""
    motivational_lines()
    exercise_library()
