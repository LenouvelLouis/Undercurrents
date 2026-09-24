"""Weather enrichment, with the HTTP call stubbed out."""

from undercurrents.clustering import weather
from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue
from undercurrents.storage import db


class StubWeather:
    def __init__(self, answers=None, fail_on=()):
        self.answers = answers or {}
        self.fail_on = set(fail_on)
        self.calls = []

    def daily(self, latitude, longitude, day):
        self.calls.append((latitude, longitude, day))
        if day in self.fail_on:
            return None
        return self.answers.get(
            day,
            {"temp_max_c": 18.0, "temp_min_c": 9.0, "precipitation_mm": 0.0, "wind_max_kmh": 12.0},
        )


def _save(conn, setlist_id, event_date, venue_id="v1", coords=(48.85, 2.35)):
    db.ensure_venues_coordinate_columns(conn)
    db.save_setlist(
        conn,
        NormalizedSetlist(
            id=setlist_id, event_date=event_date, last_updated_source="x",
            url=f"https://x/{setlist_id}",
            artist=Artist(id="a1", name="Tame Impala", mbid="a1"),
            venue=Venue(id=venue_id, name="V", city="C", state=None, country="Country A",
                        latitude=coords[0] if coords else None,
                        longitude=coords[1] if coords else None),
            tour=None,
            songs=[SetlistSongEntry(1, 1, "A", False, False, None, False, None)],
        ),
    )


def test_a_show_gets_the_weather_of_its_own_city_and_date(tmp_conn):
    _save(tmp_conn, "s1", "2020-06-15")
    client = StubWeather({"2020-06-15": {"temp_max_c": 28.0, "temp_min_c": 17.0,
                                         "precipitation_mm": 4.2, "wind_max_kmh": 22.0}})

    result = weather.enrich(tmp_conn, client=client)

    assert result["written"] == 1 and result["failed"] == 0
    assert client.calls == [(48.85, 2.35, "2020-06-15")]
    row = tmp_conn.execute("SELECT * FROM show_weather").fetchone()
    assert row["precipitation_mm"] == 4.2
    assert row["temp_max_c"] == 28.0


def test_a_show_without_coordinates_is_not_queried(tmp_conn):
    _save(tmp_conn, "s1", "2020-06-15", coords=None)
    client = StubWeather()

    result = weather.enrich(tmp_conn, client=client)

    assert result["shows_pending"] == 0
    assert client.calls == [], "no point asking the archive about a place we cannot locate"


def test_a_failed_lookup_is_counted_and_leaves_no_row(tmp_conn):
    # A partial answer written as zeros would be indistinguishable from a dry, still evening.
    _save(tmp_conn, "s1", "2020-06-15")
    result = weather.enrich(tmp_conn, client=StubWeather(fail_on={"2020-06-15"}))

    assert result["failed"] == 1 and result["written"] == 0
    assert tmp_conn.execute("SELECT COUNT(*) FROM show_weather").fetchone()[0] == 0


def test_a_second_run_only_fetches_what_is_missing(tmp_conn):
    _save(tmp_conn, "s1", "2020-06-15")
    _save(tmp_conn, "s2", "2020-06-16")
    client = StubWeather(fail_on={"2020-06-16"})
    weather.enrich(tmp_conn, client=client)

    retry = StubWeather()
    result = weather.enrich(tmp_conn, client=retry)

    assert result["shows_pending"] == 1
    assert retry.calls == [(48.85, 2.35, "2020-06-16")]
    assert tmp_conn.execute("SELECT COUNT(*) FROM show_weather").fetchone()[0] == 2


def test_the_limit_caps_a_run(tmp_conn):
    for i in range(1, 4):
        _save(tmp_conn, f"s{i}", f"2020-06-{i:02d}")
    client = StubWeather()
    result = weather.enrich(tmp_conn, client=client, limit=2)
    assert result["written"] == 2 and len(client.calls) == 2
