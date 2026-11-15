from datetime import date

from app.content import motivational_lines
from app.engines.lines_engine import line_of_the_day


def test_lines_load_and_are_unique():
    lines = motivational_lines()
    assert len(lines) >= 30
    assert len(set(lines)) == len(lines)


def test_line_is_stable_for_a_day_and_changes_daily():
    lines = motivational_lines()
    d = date(2026, 5, 1)
    assert line_of_the_day(lines, d, 1) == line_of_the_day(lines, d, 1)
    week = {line_of_the_day(lines, date(2026, 5, i), 1) for i in range(1, 8)}
    assert len(week) == 7
