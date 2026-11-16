from datetime import date, timedelta

from app.engines import progress_engine as pe

FIRST = date(2026, 1, 1)


def day(n: int) -> date:
    return FIRST + timedelta(days=n)


def test_cards_ready_every_28_days():
    assert pe.cards_ready(FIRST, day(27)) == 0
    assert pe.cards_ready(FIRST, day(28)) == 1
    assert pe.cards_ready(FIRST, day(56)) == 2
    assert pe.next_card_on(FIRST, day(30)) == day(56)


def test_no_cards_without_checkins_or_before_four_weeks():
    assert pe.build_cards("lose_fat", [], pe.DailyLog(), day(100)) == []
    pts = [pe.CheckinPoint(FIRST, 80)]
    assert pe.build_cards("lose_fat", pts, pe.DailyLog(), day(27)) == []


def test_card_compares_then_and_now():
    pts = [
        pe.CheckinPoint(day(0), 80, waist_cm=90, energy=2, stairs=3),
        pe.CheckinPoint(day(14), 79, energy=3),
        pe.CheckinPoint(day(27), 78.4, waist_cm=88, energy=4, stairs=3),
        pe.CheckinPoint(day(40), 77),  # after card 1
    ]
    log = pe.DailyLog(
        steps={day(1): 6000, day(2): 8000, day(30): 1},
        workout_days=frozenset({day(3), day(10)}),
        run_m={day(5): 5200},
        meal_days=frozenset({day(1), day(2), day(3)}),
    )
    [card] = pe.build_cards("lose_fat", pts, log, day(30))
    assert (card.number, card.start, card.end) == (1, day(0), day(27))
    assert card.now_day == day(27)
    measures = {c.name: (c.then, c.now, c.change) for c in card.measures}
    assert measures == {"weight_kg": (80, 78.4, -1.6), "waist_cm": (90, 88, -2)}
    wins = {c.name: c.change for c in card.wins}
    assert wins == {"energy": 2, "stairs": 0}
    b = card.block
    assert (b.avg_steps, b.workouts, b.run_km, b.meal_days) == (7000, 2, 5.2, 3)
    assert card.previous_block is None
    assert card.highlights == [
        "1.6 kg down since you started.",
        "Waist 2 cm smaller.",
        "Energy: up from 2 to 4 out of 5.",
        "2 workouts done in 4 weeks.",
    ]


def test_second_card_compares_steps_with_the_block_before():
    pts = [pe.CheckinPoint(day(0), 70), pe.CheckinPoint(day(50), 70.5)]
    log = pe.DailyLog(steps={day(5): 5000, day(30): 6000})
    cards = pe.build_cards("stay_fit", pts, log, day(60))
    assert [c.number for c in cards] == [2, 1]
    second = cards[0]
    assert second.previous_block is not None and second.previous_block.avg_steps == 5000
    assert second.highlights == [
        "Your weight is holding steady, right where you want it.",
        "1,000 more steps a day than the 4 weeks before.",
    ]


def test_weight_lines_follow_the_goal():
    assert pe._weight_line("lose_fat", -0.2) is None
    assert pe._weight_line("lose_fat", 1) is None
    assert pe._weight_line("build_muscle", 0.8) == "0.8 kg up since you started."
    assert pe._weight_line("stay_fit", 1.5) is None


def test_fallback_highlight_and_card_limit():
    pts = [pe.CheckinPoint(day(0), 80), pe.CheckinPoint(day(10), 81)]
    cards = pe.build_cards("lose_fat", pts, pe.DailyLog(), day(28 * 20))
    assert len(cards) == pe.MAX_CARDS and cards[0].number == 20
    assert cards[-1].highlights[0].startswith("Four more weeks")
