"""Checks Google ID tokens from Google Identity Services ("Sign in with Google").

The browser gets a signed ID token (a JWT) from Google and sends it to the API. The token
is verified here with PyJWT against Google's published signing keys: signature (RS256),
audience (our client id), issuer, expiry and a verified email. No Google library and no
call other than fetching Google's public keys (cached).
"""

import asyncio
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import jwt

from app.core.config import get_settings

GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = ("accounts.google.com", "https://accounts.google.com")
LEEWAY_S = 30


class GoogleTokenError(Exception):
    """The ID token is missing, forged, expired, for another app or has no verified email."""


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str


class GoogleVerifier(Protocol):
    async def verify(self, credential: str) -> GoogleIdentity: ...


class PyJWTGoogleVerifier:
    def __init__(self, client_id: str) -> None:
        self.client_id = client_id
        self._keys = jwt.PyJWKClient(GOOGLE_CERTS_URL, cache_keys=True, lifespan=3600)

    def _verify_sync(self, credential: str) -> GoogleIdentity:
        try:
            key = self._keys.get_signing_key_from_jwt(credential)
            claims = jwt.decode(
                credential,
                key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=GOOGLE_ISSUERS,
                leeway=LEEWAY_S,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except (jwt.PyJWTError, jwt.PyJWKClientError) as exc:
            raise GoogleTokenError(type(exc).__name__) from exc
        email = claims.get("email")
        if not email or claims.get("email_verified") is not True:
            raise GoogleTokenError("email not verified")
        return GoogleIdentity(sub=str(claims["sub"]), email=str(email).strip().lower())

    async def verify(self, credential: str) -> GoogleIdentity:
        # PyJWKClient fetches keys with blocking I/O; keep it off the event loop.
        return await asyncio.to_thread(self._verify_sync, credential)


@lru_cache
def _verifier(client_id: str) -> PyJWTGoogleVerifier:
    return PyJWTGoogleVerifier(client_id)


def get_google_verifier() -> GoogleVerifier | None:
    """FastAPI dependency: None when Sign in with Google is switched off."""
    client_id = get_settings().google_client_id
    return _verifier(client_id) if client_id else None
