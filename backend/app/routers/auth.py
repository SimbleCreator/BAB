from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status

from app.core.cookies import (
    REFRESH_COOKIE,
    clear_refresh_cookie,
    require_client_header,
    set_refresh_cookie,
)
from app.core.deps import CurrentUser, SessionDep
from app.core.rate_limit import login_limiter, register_limiter
from app.schemas.auth import (
    ChangePasswordIn,
    GoogleConfigOut,
    GoogleSignInIn,
    LoginIn,
    RegisterIn,
    TokenOut,
    UserOut,
)
from app.schemas.common import ErrorOut
from app.services import auth_service
from app.services.google_auth import GoogleVerifier, get_google_verifier

router = APIRouter(prefix="/auth", tags=["auth"])

RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]
_errors = {401: {"model": ErrorOut}, 429: {"model": ErrorOut}}


@router.post(
    "/register",
    response_model=TokenOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(register_limiter)],
    responses={409: {"model": ErrorOut}, 429: {"model": ErrorOut}},
)
async def register(data: RegisterIn, session: SessionDep, response: Response) -> TokenOut:
    result = await auth_service.register(session, data)
    set_refresh_cookie(response, result.refresh_token)
    return result.token


@router.post(
    "/login", response_model=TokenOut, dependencies=[Depends(login_limiter)], responses=_errors
)
async def login(data: LoginIn, session: SessionDep, response: Response) -> TokenOut:
    result = await auth_service.login(session, data)
    set_refresh_cookie(response, result.refresh_token)
    return result.token


@router.get(
    "/google/config",
    response_model=GoogleConfigOut,
    summary="Whether Sign in with Google is on, and the public client id for the button",
)
async def google_config() -> GoogleConfigOut:
    return auth_service.google_config()


@router.post(
    "/google",
    response_model=TokenOut,
    dependencies=[Depends(login_limiter)],
    responses={**_errors, 400: {"model": ErrorOut}, 503: {"model": ErrorOut}},
    summary="Sign in (or sign up) with a Google ID token",
    description="Matches the Google account, then the verified email (linking it). With no "
    "match a new account is created only when is_adult and accepts_privacy are true; "
    "otherwise 400 consent_required, and the client asks and sends the same token again.",
)
async def google_sign_in(
    data: GoogleSignInIn,
    session: SessionDep,
    response: Response,
    verifier: Annotated[GoogleVerifier | None, Depends(get_google_verifier)],
) -> TokenOut:
    result = await auth_service.google_sign_in(session, verifier, data)
    set_refresh_cookie(response, result.refresh_token)
    return result.token


@router.post(
    "/refresh",
    response_model=TokenOut,
    responses={**_errors, 403: {"model": ErrorOut}},
    dependencies=[Depends(require_client_header)],
    summary="Rotate the refresh cookie and get a new access token",
)
async def refresh(session: SessionDep, response: Response, token: RefreshCookie = None) -> TokenOut:
    result = await auth_service.refresh(session, token)
    set_refresh_cookie(response, result.refresh_token)
    return result.token


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_client_header)],
    responses={403: {"model": ErrorOut}},
)
async def logout(session: SessionDep, response: Response, token: RefreshCookie = None) -> None:
    await auth_service.logout(session, token)
    clear_refresh_cookie(response)


@router.get("/me", response_model=UserOut, responses=_errors)
async def me(user: CurrentUser, session: SessionDep) -> UserOut:
    return await auth_service.me(session, user)


@router.post(
    "/change-password", response_model=TokenOut, responses={**_errors, 400: {"model": ErrorOut}}
)
async def change_password(
    data: ChangePasswordIn, user: CurrentUser, session: SessionDep, response: Response
) -> TokenOut:
    result = await auth_service.change_password(session, user, data)
    set_refresh_cookie(response, result.refresh_token)
    return result.token
