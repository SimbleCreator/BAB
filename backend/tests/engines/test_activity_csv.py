from datetime import date

from app.services.activity_csv import MAX_BYTES, TEMPLATE, parse

TODAY = date(2026, 3, 10)


def csv(*lines: str) -> bytes:
    return ("\n".join(lines) + "\n").encode()


def test_template_parses_cleanly():
    parsed = parse(TEMPLATE.encode(), date(2026, 12, 31))
    assert parsed.file_errors == []
    assert len(parsed.valid) == 2
    assert parsed.rows[0].distance_m == 6200
    assert parsed.rows[1].distance_m is None


def test_row_errors_are_reported_per_line():
    parsed = parse(
        csv(
            "date,steps,distance_km,active_kcal",
            "2026-03-01,8000,5.5,300",
            "03/02/2026,8000,,",
            "2026-03-11,100,,",
            "2026-03-01,9000,,",
            "2026-03-04,lots,,",
            "2026-03-05,-5,,",
            "2026-03-06,,,",
            "",
            "2026-03-07,,999,",
        ),
        TODAY,
    )
    errors = {r.line: r.errors for r in parsed.rows}
    assert errors[2] == []
    assert "date must look like 2026-01-31" in errors[3]
    assert "date is in the future" in errors[4]
    assert "same date as line 2" in errors[5]
    assert "steps is not a number" in errors[6]
    assert errors[7] == ["steps must be between 0 and 200,000"]
    assert errors[8] == ["no numbers on this row"]
    assert 10 in errors and errors[10] == ["distance_km must be between 0 and 300"]
    assert len(parsed.valid) == 1


def test_today_is_allowed():
    parsed = parse(csv("date,steps,distance_km,active_kcal", "2026-03-10,500,,"), TODAY)
    assert parsed.valid


def test_header_case_bom_extra_columns_and_semicolons():
    content = "﻿Date;Steps;Distance_KM;Active_kcal;Extra\n2026-03-01;7000;4.2;250;x\n"
    parsed = parse(content.encode(), TODAY)
    assert parsed.file_errors == []
    assert parsed.rows[0].steps == 7000
    assert parsed.rows[0].distance_m == 4200


def test_missing_columns():
    parsed = parse(csv("date,steps", "2026-03-01,5"), TODAY)
    assert parsed.file_errors and "distance_km" in parsed.file_errors[0]


def test_too_large_and_bad_encoding_and_empty():
    assert parse(b"x" * (MAX_BYTES + 1), TODAY).file_errors == ["File is larger than 1 MB."]
    assert "UTF-8" in parse(b"\xff\xfe\x00bad", TODAY).file_errors[0]
    assert parse(b"", TODAY).file_errors == ["The file is empty."]
