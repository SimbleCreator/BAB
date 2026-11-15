from fastapi import Request, Response

from app.core.config import get_settings
from app.core.errors import ForbiddenError

REFRESH_COOKIE = "bab_refresh"
# Endpoints that act on the refresh cookie also require this header. A browser can only
# send a custom header cross-site after a CORS preflight, which the API refuses for other
# origins, so another site cannot make the browser use the cookie.
CLIENT_HEADER = "X-BAB-Client"


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


async def require_client_header(request: Request) -> None:
    if not request.headers.get(CLIENT_HEADER):
        raise ForbiddenError("Missing client header.", code="client_header_missing")
