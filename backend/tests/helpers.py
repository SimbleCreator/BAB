import httpx

PASSWORD = "correct-horse-1"

PROFILE = {
    "name": "Asha",
    "age": 30,
    "sex": "female",
    "height_cm": 162.0,
    "weight_kg": 64.5,
    "goal": "lose_fat",
    "level": "beginner",
    "minutes_per_day": 30,
    "days_per_week": 3,
    "has_pullup_bar": False,
    "diet_type": "veg",
    "daily_step_goal": 8000,
    "timezone": "Asia/Kolkata",
}


async def register(client: httpx.AsyncClient, email: str = "a@example.com") -> dict:
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": PASSWORD, "is_adult": True, "accepts_privacy": True},
    )
    assert r.status_code == 201, r.text
    return r.json()


def bearer(token_body: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_body['access_token']}"}


async def onboard(client: httpx.AsyncClient, email: str = "a@example.com", **profile) -> dict:
    """Register and finish onboarding. Returns auth headers."""
    tok = await register(client, email)
    h = bearer(tok)
    r = await client.put("/api/v1/profile", json=PROFILE | profile, headers=h)
    assert r.status_code == 200, r.text
    return h
