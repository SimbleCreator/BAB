"""Safe GPX parsing. Uses defusedxml so entity expansion and external DTDs are refused."""

from datetime import datetime, timezone
from xml.etree.ElementTree import Element, ParseError  # noqa: S405 - types only

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring

from app.engines.run_engine import TrackPoint

MAX_BYTES = 5 * 1024 * 1024
MAX_POINTS = 200_000


class GpxError(ValueError):
    pass


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(el: Element, name: str) -> str | None:
    for child in el:
        if _local(child.tag) == name:
            return (child.text or "").strip() or None
    return None


def _parse_time(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def parse_gpx(content: bytes) -> list[TrackPoint]:
    if len(content) > MAX_BYTES:
        raise GpxError("File is larger than 5 MB.")
    try:
        root = fromstring(content)
    except (ParseError, DefusedXmlException) as exc:
        raise GpxError("This does not look like a valid GPX file.") from exc
    if _local(root.tag) != "gpx":
        raise GpxError("This does not look like a valid GPX file.")

    points: list[TrackPoint] = []
    segment = 0
    for trk in (e for e in root if _local(e.tag) == "trk"):
        for seg in (e for e in trk if _local(e.tag) == "trkseg"):
            segment += 1
            for pt in (e for e in seg if _local(e.tag) == "trkpt"):
                if len(points) >= MAX_POINTS:
                    raise GpxError("This track has too many points.")
                try:
                    lat, lng = float(pt.get("lat", "")), float(pt.get("lon", ""))
                except ValueError:
                    continue
                if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                    continue
                ele_raw = _child_text(pt, "ele")
                try:
                    ele = float(ele_raw) if ele_raw is not None else None
                except ValueError:
                    ele = None
                points.append(
                    TrackPoint(lat, lng, ele, _parse_time(_child_text(pt, "time")), segment)
                )
    if len(points) < 2:
        raise GpxError("No track found in this file. Export the activity as GPX with a track.")
    if sum(1 for p in points if p.time) < 2:
        raise GpxError("This track has no times. Add the run by hand instead.")
    return points
