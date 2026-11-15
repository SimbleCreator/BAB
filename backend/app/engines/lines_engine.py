"""Picks the motivational line of the day."""

from collections.abc import Sequence
from datetime import date


def line_of_the_day(lines: Sequence[str], day: date, user_id: int) -> str:
    """Same line all day for a user; users see different lines on the same day."""
    if not lines:
        raise ValueError("no lines")
    return lines[(day.toordinal() * 7 + user_id) % len(lines)]
