from datetime import datetime, timedelta, timezone

M_PER_DEG_LAT = 2 * 3.141592653589793 * 6_371_000 / 360  # matches the engine's sphere


def track(
    n: int,
    metres_per_step: float,
    seconds_per_step: float,
    start: datetime | None = None,
    lat0: float = 12.97,
    lng0: float = 77.59,
) -> list[tuple[float, float, datetime]]:
    """Points running due north at a steady pace."""
    start = start or datetime(2026, 3, 1, 1, 0, tzinfo=timezone.utc)
    return [
        (
            lat0 + i * metres_per_step / M_PER_DEG_LAT,
            lng0,
            start + timedelta(seconds=i * seconds_per_step),
        )
        for i in range(n)
    ]


def gpx_bytes(points, *, namespace: str = "http://www.topografix.com/GPX/1/1", times=True) -> bytes:
    pts = "".join(
        f'<trkpt lat="{lat:.7f}" lon="{lng:.7f}"><ele>900.0</ele>'
        + (f"<time>{t.strftime('%Y-%m-%dT%H:%M:%SZ')}</time>" if times else "")
        + "</trkpt>"
        for lat, lng, t in points
    )
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<gpx version="1.1" creator="test" xmlns="{namespace}">'
        f"<trk><name>Test</name><trkseg>{pts}</trkseg></trk></gpx>"
    ).encode()
