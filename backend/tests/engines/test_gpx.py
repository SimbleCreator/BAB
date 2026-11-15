import pytest

from app.services.gpx import MAX_BYTES, GpxError, parse_gpx
from tests.gpx_helpers import gpx_bytes, track


def test_parses_gpx_1_1():
    pts = parse_gpx(gpx_bytes(track(5, 100, 30)))
    assert len(pts) == 5
    assert pts[0].ele_m == 900.0
    assert pts[0].time is not None and pts[0].time.tzinfo is not None


def test_parses_gpx_1_0_namespace():
    content = gpx_bytes(track(3, 100, 30), namespace="http://www.topografix.com/GPX/1/0")
    assert len(parse_gpx(content)) == 3


def test_multiple_segments_are_numbered():
    seg = "".join(
        f'<trkpt lat="1.{i}" lon="2"><time>2026-03-01T01:0{i}:00Z</time></trkpt>' for i in range(3)
    )
    content = f"<gpx><trk><trkseg>{seg}</trkseg><trkseg>{seg}</trkseg></trk></gpx>".encode()
    pts = parse_gpx(content)
    assert [p.segment for p in pts] == [1, 1, 1, 2, 2, 2]


@pytest.mark.parametrize(
    "content",
    [
        # Billion laughs style entity expansion
        b'<?xml version="1.0"?><!DOCTYPE gpx [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;">]>'
        b"<gpx><trk><trkseg><trkpt lat='1' lon='1'><name>&b;</name></trkpt></trkseg></trk></gpx>",
        # External entity (XXE)
        b'<?xml version="1.0"?><!DOCTYPE gpx [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
        b"<gpx><trk><trkseg><trkpt lat='1' lon='1'><name>&x;</name></trkpt></trkseg></trk></gpx>",
    ],
)
def test_entities_are_refused(content):
    with pytest.raises(GpxError):
        parse_gpx(content)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"not xml", "valid GPX"),
        (b"<kml></kml>", "valid GPX"),
        (b"<gpx></gpx>", "No track"),
        (gpx_bytes(track(5, 100, 30), times=False), "no times"),
        (b"x" * (MAX_BYTES + 1), "5 MB"),
    ],
)
def test_bad_files(content, message):
    with pytest.raises(GpxError, match=message):
        parse_gpx(content)


def test_out_of_range_points_are_skipped():
    good = '<trkpt lat="1" lon="1"><time>2026-03-01T01:00:00Z</time></trkpt>'
    good2 = '<trkpt lat="1.001" lon="1"><time>2026-03-01T01:01:00Z</time></trkpt>'
    bad = '<trkpt lat="95" lon="1"><time>2026-03-01T01:02:00Z</time></trkpt>'
    content = f"<gpx><trk><trkseg>{good}{bad}{good2}</trkseg></trk></gpx>".encode()
    assert len(parse_gpx(content)) == 2
