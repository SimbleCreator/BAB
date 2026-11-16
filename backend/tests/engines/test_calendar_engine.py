from datetime import date

from app.content import calendar_events
from app.engines import calendar_engine as ce


def ev(code, start, end, recurring=True, regions=(), kind="season"):
    return ce.Event(code, code, kind, recurring, start, end, regions, "tip")


def test_one_off_and_recurring():
    once = ev("once", "2027-03-21", "2027-03-23", recurring=False)
    assert ce.is_on(once, date(2027, 3, 21)) and ce.is_on(once, date(2027, 3, 23))
    assert not ce.is_on(once, date(2028, 3, 22))
    monsoon = ev("m", "06-15", "09-30")
    assert ce.is_on(monsoon, date(2026, 7, 1)) and ce.is_on(monsoon, date(2031, 9, 30))
    assert not ce.is_on(monsoon, date(2026, 6, 14))


def test_recurring_over_new_year():
    ny = ev("ny", "12-24", "01-01")
    assert ce.is_on(ny, date(2026, 12, 31)) and ce.is_on(ny, date(2027, 1, 1))
    assert not ce.is_on(ny, date(2027, 1, 2)) and not ce.is_on(ny, date(2026, 12, 23))


def test_regions_and_order():
    heat = ev("heat", "04-01", "06-15", regions=("north",))
    fest = ev("fest", "05-01", "05-02", kind="festival")
    events = (heat, fest)
    assert [e.code for e in ce.events_on(events, date(2027, 5, 1), "north")] == ["fest", "heat"]
    assert [e.code for e in ce.events_on(events, date(2027, 5, 1), "south")] == ["fest"]
    assert [e.code for e in ce.events_on(events, date(2027, 5, 1), None)] == ["fest"]


def test_events_between_lists_each_once():
    events = (ev("a", "01-01", "01-03"), ev("b", "01-05", "01-05"))
    found = ce.events_between(events, date(2027, 1, 2), 7, None)
    assert [e.code for e in found] == ["a", "b"]


def test_calendar_content_loads():
    events = calendar_events()
    assert {"monsoon", "summer_heat", "diwali_2026", "new_year"} <= {e.code for e in events}
    assert all(e.tip for e in events)
