from datetime import date, timedelta

from app.engines.checkin_engine import change, checkin_due

TODAY = date(2026, 3, 10)


def test_due_when_missing():
    assert checkin_due(None, TODAY)


def test_due_only_after_more_than_7_days():
    assert not checkin_due(TODAY, TODAY)
    assert not checkin_due(TODAY - timedelta(days=7), TODAY)
    assert checkin_due(TODAY - timedelta(days=8), TODAY)


def test_change():
    assert change(70.0, 71.5) == -1.5
    assert change(72.3, 72.0) == 0.3
    assert change(None, 70) is None
    assert change(70, None) is None
