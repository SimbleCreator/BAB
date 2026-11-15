"""CSV parsing for activity import. Pure: no database access."""

import csv
import io
from dataclasses import dataclass, field
from datetime import date

from app.schemas.activity import MAX_ACTIVE_KCAL, MAX_DISTANCE_M, MAX_STEPS

MAX_BYTES = 1024 * 1024
MAX_ROWS = 2000
COLUMNS = ("date", "steps", "distance_km", "active_kcal")
TEMPLATE = "date,steps,distance_km,active_kcal\n2026-01-15,8500,6.2,320\n2026-01-16,10200,,\n"


@dataclass
class CsvRow:
    line: int
    day: date | None = None
    steps: int | None = None
    distance_m: int | None = None
    active_kcal: int | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class ParsedCsv:
    file_errors: list[str] = field(default_factory=list)
    rows: list[CsvRow] = field(default_factory=list)

    @property
    def valid(self) -> list[CsvRow]:
        return [r for r in self.rows if not r.errors]


def _int(raw: str, name: str, maximum: int, row: CsvRow) -> int | None:
    raw = raw.strip().replace(",", "").replace("_", "")
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        row.errors.append(f"{name} is not a number")
        return None
    if value < 0 or value > maximum:
        row.errors.append(f"{name} must be between 0 and {maximum:,}")
        return None
    return round(value)


def parse(content: bytes, today: date) -> ParsedCsv:
    result = ParsedCsv()
    if len(content) > MAX_BYTES:
        result.file_errors.append("File is larger than 1 MB.")
        return result
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        result.file_errors.append("Save the file as a UTF-8 CSV and try again.")
        return result

    first_line = text.split("\n", 1)[0]
    delimiter = ";" if ";" in first_line and "," not in first_line else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        header = [h.strip().lower() for h in next(reader)]
    except (StopIteration, csv.Error):
        result.file_errors.append("The file is empty.")
        return result
    missing = [c for c in COLUMNS if c not in header]
    if missing:
        result.file_errors.append(
            f"Missing column(s): {', '.join(missing)}. Use the template's header row."
        )
        return result
    index = {c: header.index(c) for c in COLUMNS}

    seen: dict[date, int] = {}
    try:
        for line_no, cells in enumerate(reader, start=2):
            if not any(c.strip() for c in cells):
                continue
            if len(result.rows) >= MAX_ROWS:
                result.file_errors.append(f"Only the first {MAX_ROWS} rows were read.")
                break
            cells = cells + [""] * (len(header) - len(cells))
            row = CsvRow(line=line_no)
            raw_day = cells[index["date"]].strip()
            try:
                row.day = date.fromisoformat(raw_day)
            except ValueError:
                row.errors.append("date must look like 2026-01-31")
            if row.day is not None:
                if row.day > today:
                    row.errors.append("date is in the future")
                elif row.day in seen:
                    row.errors.append(f"same date as line {seen[row.day]}")
                else:
                    seen[row.day] = line_no
            row.steps = _int(cells[index["steps"]], "steps", MAX_STEPS, row)
            km = _distance_km(cells[index["distance_km"]], row)
            row.distance_m = round(km * 1000) if km is not None else None
            row.active_kcal = _int(cells[index["active_kcal"]], "active_kcal", MAX_ACTIVE_KCAL, row)
            if (
                not row.errors
                and row.steps is None
                and row.distance_m is None
                and row.active_kcal is None
            ):
                row.errors.append("no numbers on this row")
            result.rows.append(row)
    except csv.Error:
        result.file_errors.append("The file could not be read as CSV.")
    return result


def _distance_km(raw: str, row: CsvRow) -> float | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        row.errors.append("distance_km is not a number")
        return None
    if value < 0 or value * 1000 > MAX_DISTANCE_M:
        row.errors.append(f"distance_km must be between 0 and {MAX_DISTANCE_M // 1000}")
        return None
    return value
