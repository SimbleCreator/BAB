from fastapi import Response

from app.core.config import get_settings

REFRESH_COOKIE = "bab_refresh"


def set_refresh_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=s.refresh_token_days * 24 * 3600,
        path=s.refresh_cookie_path,
        httponly=True,
        secure=True,
        samesite=s.cookie_samesite,
    )


def clear_refresh_cookie(response: Response) -> None:
    s = get_settings()
    response.delete_cookie(
        REFRESH_COOKIE,
        path=s.refresh_cookie_path,
        httponly=True,
        secure=True,
        samesite=s.cookie_samesite,
    )
