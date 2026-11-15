from fastapi import APIRouter, Depends, Response, status

from app.core.cookies import clear_refresh_cookie
from app.core.deps import AdminUser, CurrentUser, SessionDep
from app.core.rate_limit import login_limiter
from app.schemas.account import AdminStatsOut, DeleteAccountIn, ExportOut, PublicConfigOut
from app.schemas.common import ErrorOut
from app.services import account_service

router = APIRouter(tags=["account"])


@router.get(
    "/account/export",
    response_model=ExportOut,
    summary="Download everything stored for the signed-in user as one JSON file",
)
async def export(user: CurrentUser, session: SessionDep, response: Response) -> ExportOut:
    data = await account_service.export(session, user)
    response.headers["Content-Disposition"] = (
        f'attachment; filename="bab-export-{data.exported_at:%Y-%m-%d}.json"'
    )
    response.headers["Cache-Control"] = "no-store"
    return data


@router.post(
    "/account/delete",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(login_limiter)],
    responses={400: {"model": ErrorOut}, 429: {"model": ErrorOut}},
    summary="Permanently delete the account and all of its data (password required)",
)
async def delete_account(
    data: DeleteAccountIn, user: CurrentUser, session: SessionDep, response: Response
) -> None:
    await account_service.delete_account(session, user, data)
    clear_refresh_cookie(response)


@router.get("/config/public", response_model=PublicConfigOut, summary="App name and contact email")
async def public_config() -> PublicConfigOut:
    return account_service.public_config()


@router.get(
    "/admin/stats",
    response_model=AdminStatsOut,
    responses={403: {"model": ErrorOut}},
    summary="Aggregate numbers for admins. No individual's data.",
)
async def admin_stats(_: AdminUser, session: SessionDep) -> AdminStatsOut:
    return await account_service.admin_stats(session)
