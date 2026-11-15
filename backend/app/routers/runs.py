from typing import Annotated

from fastapi import APIRouter, File, Form, Query, UploadFile, status

from app.core.deps import CurrentUser, SessionDep
from app.schemas.common import ErrorOut
from app.schemas.run import RunDetailOut, RunIn, RunListOut, RunPatch
from app.services import gpx, run_service

router = APIRouter(prefix="/runs", tags=["runs"])

_errors = {400: {"model": ErrorOut}, 409: {"model": ErrorOut}}
_missing = {404: {"model": ErrorOut}}


@router.get("", response_model=RunListOut)
async def list_runs(
    user: CurrentUser,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RunListOut:
    return await run_service.list_runs(session, user, limit, offset)


@router.post(
    "", response_model=RunDetailOut, status_code=status.HTTP_201_CREATED, responses=_errors
)
async def create_run(data: RunIn, user: CurrentUser, session: SessionDep) -> RunDetailOut:
    return await run_service.create_manual(session, user, data)


@router.post(
    "/gpx",
    response_model=RunDetailOut,
    status_code=status.HTTP_201_CREATED,
    responses=_errors,
    summary="Create a run from a GPX file (at most 5 MB). The file is not kept.",
)
async def upload_gpx(
    user: CurrentUser,
    session: SessionDep,
    file: Annotated[UploadFile, File(description="GPX file, at most 5 MB")],
    note: Annotated[str | None, Form(max_length=500)] = None,
) -> RunDetailOut:
    content = await file.read(gpx.MAX_BYTES + 1)
    return await run_service.create_from_gpx(session, user, content, note)


@router.get("/{run_id}", response_model=RunDetailOut, responses=_missing)
async def get_run(run_id: int, user: CurrentUser, session: SessionDep) -> RunDetailOut:
    return await run_service.get_run(session, user, run_id)


@router.patch("/{run_id}", response_model=RunDetailOut, responses={**_missing, **_errors})
async def update_run(
    run_id: int, data: RunPatch, user: CurrentUser, session: SessionDep
) -> RunDetailOut:
    return await run_service.update_run(session, user, run_id, data)


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT, responses=_missing)
async def delete_run(run_id: int, user: CurrentUser, session: SessionDep) -> None:
    await run_service.delete_run(session, user, run_id)
