import json
from datetime import timedelta

import pytest
from sqlalchemy import update

from app.core.timeutil import local_today
from app.models import BounceLetter
from app.services.bounce.llm import LLMError, get_llm
from tests.bounce_helpers import FakeLLM
from tests.helpers import PROFILE, onboard

pytestmark = pytest.mark.anyio

URL = "/api/v1/bounce/letter"
GOOD = [
    "It is morning and I just got back from my walk. The first weeks felt slow, but the "
    "walks after dinner became the part of the day I look forward to.",
    "I still eat idli and sambar most days, just in better amounts, with a bowl of curd on "
    "the side. I stopped thinking of food as the enemy.",
    "There were rough weeks. I took easy days, came back, and kept checking in. That is what "
    "changed things: not being perfect, just showing up again.",
]


def letter(paragraphs=None) -> str:
    return json.dumps({"paragraphs": paragraphs or GOOD})


def use(client, llm):
    client._transport.app.dependency_overrides[get_llm] = lambda: llm
    return llm


def today():
    return local_today(PROFILE["timezone"])


async def test_disabled_without_ai(client):
    h = await onboard(client)
    use(client, None)
    s = (await client.get(URL, headers=h)).json()
    assert s["enabled"] is False and s["state"] == "none" and s["can_write"] is False
    assert (await client.post(URL, headers=h)).status_code == 503


async def test_write_seal_and_open(client, session):
    h = await onboard(client, usual_foods=["idli", "sambar"], wake_time="06:00")
    llm = use(client, FakeLLM(letter()))
    s = (await client.get(URL, headers=h)).json()
    assert s["state"] == "none" and s["can_write"] is True

    r = await client.post(URL, headers=h)
    assert r.status_code == 200, r.text
    s = r.json()
    assert s["state"] == "sealed" and s["days_left"] == 90
    assert s["open_on"] == str(today() + timedelta(days=90))
    assert s["letter"] is None and s["then"] is None  # sealed: the text stays hidden
    assert s["can_write"] is False
    # The name is not sent to the AI service; the usual foods are.
    prompt = llm.calls[0][0]["content"]
    assert PROFILE["name"] not in prompt and '"Idli"' in prompt and '"wake_time": "06:00"' in prompt

    again = await client.post(URL, headers=h)
    assert again.status_code == 409 and again.json()["code"] == "letter_sealed"
    early = await client.post(f"{URL}/open", headers=h)
    assert early.status_code == 409 and early.json()["code"] == "letter_not_ready"

    # 90 days pass.
    await session.execute(
        update(BounceLetter).values(written_on=today() - timedelta(days=90), open_on=today())
    )
    await session.commit()
    assert (await client.get(URL, headers=h)).json()["state"] == "ready"
    s = (await client.post(f"{URL}/open", headers=h)).json()
    assert s["state"] == "opened" and s["can_write"] is True
    assert s["letter"]["greeting"] == f"Dear {PROFILE['name']},"
    assert s["letter"]["paragraphs"] == GOOD
    assert s["letter"]["sign_off"] == "You, 90 days from now"
    assert s["then"]["weight_kg"] == PROFILE["weight_kg"] and s["now"] is not None
    # Opening again is fine; a new letter can be written.
    assert (await client.post(f"{URL}/open", headers=h)).status_code == 200
    r = await client.post(URL, headers=h)
    assert r.status_code == 200 and r.json()["state"] == "sealed"


async def test_unsafe_sentences_removed_and_retry(client):
    h = await onboard(client)
    risky = [GOOD[0] + " I lost 7 kg by now, guaranteed.", GOOD[1], GOOD[2]]
    use(client, FakeLLM(letter(risky)))
    await client.post(URL, headers=h)
    # The letter is still sealed, so read what was stored through the data export.
    data = (await client.get("/api/v1/account/export", headers=h)).json()
    text = " ".join(data["bounce_letters"][0]["content"]["paragraphs"])
    assert "kg" not in text and "guaranteed" not in text and "walk" in text


async def test_too_short_is_retried_then_rejected(client):
    h = await onboard(client)
    llm = use(client, FakeLLM(letter(["Keep going.", "You can."])))
    r = await client.post(URL, headers=h)
    assert r.status_code == 502 and r.json()["code"] == "model_bad_output"
    assert len(llm.calls) == 2 and "too short" in llm.calls[1][-1]["content"]
    llm = use(client, FakeLLM("not json", letter()))
    assert (await client.post(URL, headers=h)).status_code == 200


async def test_repeated_paragraphs_key_is_merged(client):
    # Some free models write the key once per paragraph.
    h = await onboard(client)
    raw = "{" + ", ".join(f'"paragraphs": [{json.dumps(p)}]' for p in GOOD) + "}"
    use(client, FakeLLM(raw))
    r = await client.post(URL, headers=h)
    assert r.status_code == 200, r.text
    data = (await client.get("/api/v1/account/export", headers=h)).json()
    assert data["bounce_letters"][0]["content"]["paragraphs"] == GOOD


async def test_model_error(client):
    h = await onboard(client)
    use(client, FakeLLM(LLMError("busy", code="model_busy")))
    r = await client.post(URL, headers=h)
    assert r.status_code == 502


async def test_letters_are_per_user(client):
    a = await onboard(client)
    use(client, FakeLLM(letter()))
    await client.post(URL, headers=a)
    b = await onboard(client, "b@example.com")
    assert (await client.get(URL, headers=b)).json()["state"] == "none"
    assert (await client.post(f"{URL}/open", headers=b)).status_code == 404
