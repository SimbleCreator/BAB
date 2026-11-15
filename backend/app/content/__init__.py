"""Built-in content loaded from JSON files in this folder."""

import json
from functools import lru_cache
from pathlib import Path

CONTENT_DIR = Path(__file__).resolve().parent


def _read(name: str) -> dict:
    with (CONTENT_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def motivational_lines() -> tuple[str, ...]:
    lines = _read("lines.json")["lines"]
    if not lines or not all(isinstance(x, str) and x.strip() for x in lines):
        raise ValueError("lines.json must hold a non-empty list of strings")
    return tuple(lines)


def load_all() -> None:
    """Load and validate every content file. Called at startup so bad content fails fast."""
    motivational_lines()
