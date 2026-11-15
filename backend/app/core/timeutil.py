from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo


def local_today(tz_name: str, now: datetime | None = None) -> date:
    """The user's current calendar date in their profile timezone."""
    now = now or datetime.now(timezone.utc)
    return now.astimezone(ZoneInfo(tz_name)).date()
