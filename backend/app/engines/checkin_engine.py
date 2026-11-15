"""Weekly check-in rules."""

from datetime import date

CHECKIN_INTERVAL_DAYS = 7


def checkin_due(last_day: date | None, today: date) -> bool:
    """Due when there is no check-in, or the last one is more than 7 days old."""
    return last_day is None or (today - last_day).days > CHECKIN_INTERVAL_DAYS


def change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None:
        return None
    return round(current - previous, 1)
