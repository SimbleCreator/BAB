from datetime import date, timedelta

import pytest

from app.services.bounce import letter_rules as lr

TODAY = date(2026, 11, 17)


def test_state_and_open_day():
    assert lr.open_on(TODAY) == TODAY + timedelta(days=90)
    assert lr.state(None, False, TODAY) == "none"
    assert lr.state(TODAY, False, TODAY + timedelta(days=89)) == "sealed"
    assert lr.state(TODAY, False, TODAY + timedelta(days=90)) == "ready"
    assert lr.state(TODAY, True, TODAY + timedelta(days=95)) == "opened"


@pytest.mark.parametrize(
    "sentence",
    [
        "I lost 6 kg and feel great.",
        "Down 3.5 kilos already!",
        "My waist is 4 inches smaller.",
        "This plan is guaranteed to work.",
        "I promise you will get there.",
        "You will definitely see results.",
        "Fat burners helped a lot.",
        "It cured my back pain.",
    ],
)
def test_unsafe_sentences_are_removed(sentence):
    keep = "I walk every morning now."
    assert lr.clean([f"{keep} {sentence}"]) == [keep]


def test_clean_keeps_safe_text_and_limits_paragraphs():
    paras = [f"Paragraph {i}. I kept going." for i in range(6)] + ["   "]
    out = lr.clean(paras)
    assert len(out) == lr.MAX_PARAGRAPHS and out[0] == "Paragraph 0. I kept going."
    assert lr.clean(["I lost 5 kg."]) == []


def test_problem():
    words = " ".join(["word"] * 40) + "."
    assert lr.problem([words]) is not None  # one paragraph
    assert "short" in lr.problem(["Too short.", "Still short."])
    assert lr.problem([words, words]) is None
    assert "long" in lr.problem([" ".join(["w"] * 400), words])
