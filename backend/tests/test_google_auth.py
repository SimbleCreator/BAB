import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.core.config import get_settings
from app.services import google_auth
from app.services.google_auth import (
    GoogleIdentity,
    GoogleTokenError,
    PyJWTGoogleVerifier,
    get_google_verifier,
)
from tests.helpers import PASSWORD, bearer, register

pytestmark = pytest.mark.anyio

URL = "/api/v1/auth/google"
CRED = "x" * 40  # the fake verifier ignores the token's content


class FakeVerifier:
    def __init__(self, sub="g-123", email="g@example.com", fail=False):
        self.identity = GoogleIdentity(sub, email)
        self.fail = fail

    async def verify(self, credential: str) -> GoogleIdentity:
        if self.fail:
            raise GoogleTokenError("bad")
        return self.identity


def use(client, verifier):
    client._transport.app.dependency_overrides[get_google_verifier] = lambda: verifier
    return verifier


CONSENT = {"is_adult": True, "accepts_privacy": True}


async def test_config_off_by_default(client):
    r = await client.get("/api/v1/auth/google/config")
    assert r.json() == {"enabled": False, "client_id": None}
    use(client, None)
    r = await client.post(URL, json={"credential": CRED})
    assert r.status_code == 503 and r.json()["code"] == "google_disabled"


async def test_config_on(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "google_client_id", "abc.apps.googleusercontent.com")
    r = await client.get("/api/v1/auth/google/config")
    assert r.json() == {"enabled": True, "client_id": "abc.apps.googleusercontent.com"}


async def test_new_user_needs_consent_then_is_created(client):
    use(client, FakeVerifier())
    r = await client.post(URL, json={"credential": CRED})
    assert r.status_code == 400 and r.json()["code"] == "consent_required"
    r = await client.post(URL, json={"credential": CRED, "is_adult": True})
    assert r.json()["code"] == "consent_required"
    r = await client.post(URL, json={"credential": CRED} | CONSENT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["email"] == "g@example.com"
    assert body["user"]["has_password"] is False and body["user"]["google_linked"] is True
    assert "bab_refresh" in r.headers.get("set-cookie", "")
    # Next time: no consent needed, same account.
    again = await client.post(URL, json={"credential": CRED})
    assert again.status_code == 200 and again.json()["user"]["id"] == body["user"]["id"]


async def test_links_existing_password_account_by_email(client):
    tok = await register(client, "g@example.com")
    use(client, FakeVerifier(email="g@example.com"))
    r = await client.post(URL, json={"credential": CRED})
    assert r.status_code == 200
    user = r.json()["user"]
    assert user["id"] == tok["user"]["id"]
    assert user["has_password"] is True and user["google_linked"] is True
    # Password sign-in still works.
    r = await client.post(
        "/api/v1/auth/login", json={"email": "g@example.com", "password": PASSWORD}
    )
    assert r.status_code == 200


async def test_matches_by_google_id_even_if_email_changed(client):
    use(client, FakeVerifier(email="old@example.com"))
    first = (await client.post(URL, json={"credential": CRED} | CONSENT)).json()
    use(client, FakeVerifier(email="new@example.com"))
    r = await client.post(URL, json={"credential": CRED})
    assert r.json()["user"]["id"] == first["user"]["id"]


async def test_email_linked_to_another_google_account_is_refused(client):
    use(client, FakeVerifier(sub="one", email="g@example.com"))
    await client.post(URL, json={"credential": CRED} | CONSENT)
    use(client, FakeVerifier(sub="two", email="g@example.com"))
    r = await client.post(URL, json={"credential": CRED} | CONSENT)
    assert r.status_code == 401 and r.json()["code"] == "google_mismatch"


async def test_bad_token_and_disabled_account(client, session):
    use(client, FakeVerifier(fail=True))
    r = await client.post(URL, json={"credential": CRED} | CONSENT)
    assert r.status_code == 401 and r.json()["code"] == "google_invalid"
    assert (await client.post(URL, json={"credential": "short"})).status_code == 422

    from sqlalchemy import update

    from app.models import User

    use(client, FakeVerifier())
    await client.post(URL, json={"credential": CRED} | CONSENT)
    await session.execute(update(User).values(is_active=False))
    await session.commit()
    r = await client.post(URL, json={"credential": CRED})
    assert r.status_code == 401 and r.json()["code"] == "account_disabled"


async def test_google_only_account_password_rules(client):
    use(client, FakeVerifier())
    h = bearer((await client.post(URL, json={"credential": CRED} | CONSENT)).json())
    # No password yet: email sign-in points to Google.
    r = await client.post(
        "/api/v1/auth/login", json={"email": "g@example.com", "password": "anything-1"}
    )
    assert r.status_code == 401 and r.json()["code"] == "use_google"
    # Set a first password without a current one.
    r = await client.post(
        "/api/v1/auth/change-password", json={"new_password": PASSWORD}, headers=h
    )
    assert r.status_code == 200 and r.json()["user"]["has_password"] is True
    h = bearer(r.json())
    # Now the current password is required.
    r = await client.post(
        "/api/v1/auth/change-password", json={"new_password": "another-pass-1"}, headers=h
    )
    assert r.status_code == 400 and r.json()["code"] == "wrong_password"
    r = await client.post(
        "/api/v1/auth/login", json={"email": "g@example.com", "password": PASSWORD}
    )
    assert r.status_code == 200


async def test_google_only_account_deletes_with_email(client):
    use(client, FakeVerifier())
    h = bearer((await client.post(URL, json={"credential": CRED} | CONSENT)).json())
    r = await client.post(
        "/api/v1/account/delete", json={"email": "other@example.com", "confirm": True}, headers=h
    )
    assert r.status_code == 400 and r.json()["code"] == "wrong_email"
    r = await client.post(
        "/api/v1/account/delete", json={"email": " G@example.com ", "confirm": True}, headers=h
    )
    assert r.status_code == 204


# The real verifier, with a locally generated RSA key standing in for Google's ----------


class _Key:
    def __init__(self, key):
        self.key = key


@pytest.fixture
def signer(monkeypatch):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = PyJWTGoogleVerifier("my-client")
    monkeypatch.setattr(
        verifier._keys, "get_signing_key_from_jwt", lambda token: _Key(private.public_key())
    )

    def sign(**claims):
        now = int(time.time())
        base = {
            "iss": "https://accounts.google.com",
            "aud": "my-client",
            "sub": "1234",
            "email": "Person@Example.com",
            "email_verified": True,
            "iat": now,
            "exp": now + 600,
        }
        return jwt.encode(base | claims, private, algorithm="RS256")

    return verifier, sign


async def test_real_verifier_accepts_good_token(signer):
    verifier, sign = signer
    assert await verifier.verify(sign()) == GoogleIdentity("1234", "person@example.com")


@pytest.mark.parametrize(
    "claims",
    [
        {"aud": "someone-else"},
        {"iss": "https://evil.example.com"},
        {"exp": int(time.time()) - 120},
        {"email_verified": False},
        {"email": None},
    ],
)
async def test_real_verifier_rejects(signer, claims):
    verifier, sign = signer
    with pytest.raises(GoogleTokenError):
        await verifier.verify(sign(**claims))


async def test_real_verifier_rejects_other_signature(signer):
    verifier, _ = signer
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = jwt.encode(
        {"iss": "accounts.google.com", "aud": "my-client", "sub": "1", "exp": 9e9, "iat": 1},
        other,
        algorithm="RS256",
    )
    with pytest.raises(GoogleTokenError):
        await verifier.verify(token)


def test_verifier_off_without_client_id(monkeypatch):
    monkeypatch.setattr(get_settings(), "google_client_id", "")
    assert google_auth.get_google_verifier() is None
