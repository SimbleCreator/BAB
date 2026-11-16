from fastapi import APIRouter

from app.core.deps import CurrentUser, SessionDep
from app.schemas.common import ErrorOut
from app.schemas.progress import ProgressOut
from app.services import progress_service

router = APIRouter(prefix="/progress", tags=["progress"])


@router.get(
    "",
    response_model=ProgressOut,
    responses={404: {"model": ErrorOut}},
    summary="Weeks to the target weight (an estimate) and then-vs-now cards every 4 weeks",
)
async def get_progress(user: CurrentUser, session: SessionDep) -> ProgressOut:
    return await progress_service.get(session, user)
