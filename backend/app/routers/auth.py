from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status

from app.core.cookies import REFRESH_COOKIE, clear_refresh_cookie, set_refresh_cookie
from app.core.deps import CurrentUser, SessionDep
from app.core.rate_limit import login_limiter, register_limiter
from app.schemas.auth import ChangePasswordIn, LoginIn, RegisterIn, TokenOut, UserOut
from app.schemas.common import ErrorOut
from app.services import auth_service

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


@router.post(
    "/refresh",
    response_model=TokenOut,
    responses=_errors,
    summary="Rotate the refresh cookie and get a new access token",
)
async def refresh(session: SessionDep, response: Response, token: RefreshCookie = None) -> TokenOut:
    result = await auth_service.refresh(session, token)
    set_refresh_cookie(response, result.refresh_token)
    return result.token


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
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
