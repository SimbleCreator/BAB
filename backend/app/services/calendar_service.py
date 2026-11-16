"""Festival, fasting and season events for a user's region."""

from datetime import date

from app.content import calendar_events, region_for
from app.engines import calendar_engine
from app.models.profile import Profile
from app.schemas.today import EventOut


def events_today(profile: Profile, today: date) -> list[EventOut]:
    region = region_for(profile.state)
    return [
        EventOut(code=e.code, name=e.name, kind=e.kind, tip=e.tip)
        for e in calendar_engine.events_on(calendar_events(), today, region)
    ]


def events_in_week(profile: Profile, start: date) -> list[calendar_engine.Event]:
    return calendar_engine.events_between(calendar_events(), start, 7, region_for(profile.state))
