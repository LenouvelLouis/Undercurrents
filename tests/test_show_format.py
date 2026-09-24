from datetime import date, timedelta

from undercurrents.derived import show_format


def _show(i, venue, songs=18, info=None, kind=None, outdoor=None, day=None, venue_id=None, duration=None):
    d = day or date(2022, 1, 1) + timedelta(days=i * 3)
    return {
        "id": f"s{i}", "event_date": d.isoformat(), "date": d, "info": info, "venue_id": venue_id or f"v{i}",
        "venue": venue, "venue_kind": kind, "is_outdoor": outdoor, "songs": songs, "duration_ms": duration,
    }


def _context():
    return [_show(i, f"Arena {i}", songs=20, duration=90 * 60000) for i in range(10)]


def test_festival_ground_and_short_set_make_a_festival():
    shows = _context() + [_show(20, "Zilker Park", songs=13, duration=60 * 60000, day=date(2022, 1, 15))]
    result = show_format.classify_all(shows)["s20"]
    assert result["format"] == "festival"
    assert any("festival ground" in s for s in result["signals"])


def test_arena_stays_a_headline_show():
    shows = _context()
    assert show_format.classify_all(shows)["s3"]["format"] == "headline"


def test_tv_dj_and_thin_setlists_are_set_apart():
    shows = _context() + [
        _show(30, "Late Show With Stephen Colbert", songs=2),
        _show(31, "Some Club", info="DJ set. Supporting Justice."),
        _show(32, "Some Theatre", songs=3),
    ]
    result = show_format.classify_all(shows)
    assert result["s30"]["format"] == "special"
    assert result["s31"]["format"] == "dj_set"
    assert result["s32"]["format"] == "incomplete"


def test_two_weekend_festival_pattern_adds_a_signal():
    a = _show(40, "Empire Polo Club", venue_id="polo", day=date(2022, 4, 15))
    b = _show(41, "Empire Polo Club", venue_id="polo", day=date(2022, 4, 22))
    result = show_format.classify_all(_context() + [a, b])
    assert result["s40"]["format"] == "festival"
    assert any("week apart" in s for s in result["s41"]["signals"])
