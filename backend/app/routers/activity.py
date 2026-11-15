from datetime import date
from typing import Annotated

from fastapi import APIRouter, File, Form, Query, Response, UploadFile, status

from app.core.deps import CurrentUser, SessionDep
from app.schemas.activity import (
    ActivityIn,
    ActivityOut,
    ActivitySummaryOut,
    CsvImportOut,
    CsvPreviewOut,
)
from app.schemas.common import ErrorOut
from app.services import activity_csv, activity_service

router = APIRouter(prefix="/activity", tags=["activity"])

_errors = {400: {"model": ErrorOut}, 409: {"model": ErrorOut}}
CsvFile = Annotated[UploadFile, File(description="CSV, at most 1 MB")]


async def _read_limited(upload: UploadFile) -> bytes:
    # Read one byte past the limit so the parser can report "too large".
    return await upload.read(activity_csv.MAX_BYTES + 1)


@router.get("", response_model=list[ActivityOut], responses=_errors)
async def list_activity(
    user: CurrentUser,
    session: SessionDep,
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
) -> list[ActivityOut]:
    return await activity_service.list_days(session, user, start, end)


@router.get("/summary", response_model=ActivitySummaryOut, responses=_errors)
async def activity_summary(
    user: CurrentUser,
    session: SessionDep,
    days: Annotated[int, Query(ge=1, le=90)] = 30,
) -> ActivitySummaryOut:
    return await activity_service.summary(session, user, days)


@router.get(
    "/csv-template",
    response_class=Response,
    responses={200: {"content": {"text/csv": {"schema": {"type": "string"}}}}},
    summary="Download the CSV import template",
)
async def csv_template() -> Response:
    return Response(
        activity_csv.TEMPLATE,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="bab-activity-template.csv"'},
    )


@router.post("/import/preview", response_model=CsvPreviewOut, responses=_errors)
async def csv_preview(user: CurrentUser, session: SessionDep, file: CsvFile) -> CsvPreviewOut:
    return await activity_service.csv_preview(session, user, await _read_limited(file))


@router.post("/import", response_model=CsvImportOut, responses=_errors)
async def csv_import(
    user: CurrentUser,
    session: SessionDep,
    file: CsvFile,
    overwrite: Annotated[bool, Form()] = False,
) -> CsvImportOut:
    return await activity_service.csv_import(session, user, await _read_limited(file), overwrite)


@router.get("/{day}", response_model=ActivityOut, responses={404: {"model": ErrorOut}, **_errors})
async def get_activity(day: date, user: CurrentUser, session: SessionDep) -> ActivityOut:
    return await activity_service.get_day(session, user, day)


@router.put("/{day}", response_model=ActivityOut, responses=_errors)
async def save_activity(
    day: date, data: ActivityIn, user: CurrentUser, session: SessionDep
) -> ActivityOut:
    return await activity_service.save_day(session, user, day, data)


@router.delete(
    "/{day}", status_code=status.HTTP_204_NO_CONTENT, responses={404: {"model": ErrorOut}}
)
async def delete_activity(day: date, user: CurrentUser, session: SessionDep) -> None:
    await activity_service.delete_day(session, user, day)
