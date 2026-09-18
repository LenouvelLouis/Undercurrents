from undercurrents.derived import features
from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue
from undercurrents.storage import db


def _save(conn, setlist_id, event_date, songs):
    db.save_setlist(
        conn,
        NormalizedSetlist(
            id=setlist_id,
            event_date=event_date,
            last_updated_source="x",
            url=f"https://x/{setlist_id}",
            artist=Artist(id="a1", name="Tame Impala", mbid="a1"),
            venue=Venue(id="v1", name="Venue", city="City", state=None, country="Country A"),
            tour=None,
            songs=songs,
        ),
    )


def _entry(position, name, encore=False, cover=False, tape=False):
    return SetlistSongEntry(position, 1, name, encore, cover, "Someone" if cover else None, tape, None)


def test_song_features_count_plays_openers_and_closers(tmp_conn):
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "Opener"), _entry(2, "Closer")])
    _save(tmp_conn, "s2", "2020-02-01", [_entry(1, "Opener"), _entry(2, "Closer")])
    features.rebuild(tmp_conn)

    rows = {
        r["song_name"]: r
        for r in tmp_conn.execute(
            "SELECT s.name AS song_name, f.* FROM song_features f JOIN songs s ON s.id = f.song_id"
        )
    }
    assert rows["Opener"]["play_count"] == 2
    assert rows["Opener"]["opener_count"] == 2
    assert rows["Opener"]["closer_count"] == 0
    assert rows["Closer"]["closer_count"] == 2
    assert rows["Opener"]["first_played"] == "2020-01-01"
    assert rows["Opener"]["last_played"] == "2020-02-01"


def test_song_features_streak_is_zero_when_absent_from_the_latest_show(tmp_conn):
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "Old"), _entry(2, "Always")])
    _save(tmp_conn, "s2", "2020-02-01", [_entry(1, "Always")])
    _save(tmp_conn, "s3", "2020-03-01", [_entry(1, "Always")])
    features.rebuild(tmp_conn)

    rows = {
        r["song_name"]: r["current_streak"]
        for r in tmp_conn.execute(
            "SELECT s.name AS song_name, f.current_streak FROM song_features f JOIN songs s ON s.id = f.song_id"
        )
    }
    assert rows["Always"] == 3
    assert rows["Old"] == 0


def test_song_features_longest_gap_uses_real_dates(tmp_conn):
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "Rare")])
    _save(tmp_conn, "s2", "2020-01-11", [_entry(1, "Rare")])
    _save(tmp_conn, "s3", "2020-04-10", [_entry(1, "Rare")])
    features.rebuild(tmp_conn)

    gap = tmp_conn.execute("SELECT longest_gap_days FROM song_features").fetchone()[0]
    assert gap == 90


def test_tape_entries_are_excluded_from_song_features_but_counted_per_show(tmp_conn):
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "Intro", tape=True), _entry(2, "Real")])
    features.rebuild(tmp_conn)

    names = [r[0] for r in tmp_conn.execute(
        "SELECT s.name FROM song_features f JOIN songs s ON s.id = f.song_id"
    )]
    assert names == ["Real"]

    row = tmp_conn.execute(
        "SELECT song_count, tape_count, opener_song_id FROM setlist_features"
    ).fetchone()
    assert row["song_count"] == 1
    assert row["tape_count"] == 1
    assert row["opener_song_id"] == db.get_song_id_by_name(tmp_conn, "Real")


def test_setlist_novelty_compares_against_the_previous_show(tmp_conn):
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "A"), _entry(2, "B")])
    # one of two songs is new -> 0.5
    _save(tmp_conn, "s2", "2020-01-05", [_entry(1, "A"), _entry(2, "C")])
    features.rebuild(tmp_conn)

    rows = {
        r["event_date"]: r
        for r in tmp_conn.execute(
            "SELECT event_date, novelty_rate, days_since_previous FROM setlist_features"
        )
    }
    assert rows["2020-01-01"]["novelty_rate"] is None
    assert rows["2020-01-01"]["days_since_previous"] is None
    assert rows["2020-01-05"]["novelty_rate"] == 0.5
    assert rows["2020-01-05"]["days_since_previous"] == 4


def test_duration_complete_only_when_every_song_has_one(tmp_conn):
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "A"), _entry(2, "B")])
    db.ensure_songs_enrichment_columns(tmp_conn)
    db.set_song_metadata(tmp_conn, db.get_song_id_by_name(tmp_conn, "A"), None, 200_000, None)
    features.rebuild(tmp_conn)
    assert tmp_conn.execute("SELECT duration_complete FROM setlist_features").fetchone()[0] == 0

    db.set_song_metadata(tmp_conn, db.get_song_id_by_name(tmp_conn, "B"), None, 100_000, None)
    features.rebuild(tmp_conn)
    row = tmp_conn.execute("SELECT duration_complete, known_duration_ms FROM setlist_features").fetchone()
    assert row["duration_complete"] == 1
    assert row["known_duration_ms"] == 300_000


def test_rebuild_is_idempotent(tmp_conn):
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "A")])
    first = features.rebuild(tmp_conn)
    second = features.rebuild(tmp_conn)
    assert first == second
    assert tmp_conn.execute("SELECT COUNT(*) FROM song_features").fetchone()[0] == 1


def _save_at(conn, setlist_id, event_date, venue_id, songs):
    """Same as _save but lets the show sit in its own venue, so travel can be measured."""
    db.save_setlist(
        conn,
        NormalizedSetlist(
            id=setlist_id,
            event_date=event_date,
            last_updated_source="x",
            url=f"https://x/{setlist_id}",
            artist=Artist(id="a1", name="Tame Impala", mbid="a1"),
            venue=Venue(id=venue_id, name=venue_id, city=venue_id, state=None, country="Country A"),
            tour=None,
            songs=songs,
        ),
    )


def test_haversine_matches_a_known_city_pair():
    # Paris to London, great-circle, is a little over 340 km on every reference table.
    km = features.haversine_km(48.8566, 2.3522, 51.5074, -0.1278)
    assert 340 < km < 347


def test_travel_km_is_null_rather_than_zero_when_a_venue_has_no_coordinates(tmp_conn):
    _save_at(tmp_conn, "s1", "2020-01-01", "v1", [_entry(1, "A")])
    _save_at(tmp_conn, "s2", "2020-01-05", "v2", [_entry(1, "A")])
    tmp_conn.execute("UPDATE venues SET latitude = 48.8566, longitude = 2.3522 WHERE id = 'v1'")
    features.rebuild(tmp_conn)

    rows = {r["event_date"]: r["travel_km"] for r in tmp_conn.execute("SELECT event_date, travel_km FROM setlist_features")}
    # The first show has no predecessor and the second lands in a venue without coordinates:
    # an unknown leg must stay unknown, never be reported as a zero-kilometre hop.
    assert rows["2020-01-01"] is None
    assert rows["2020-01-05"] is None


def test_travel_km_measures_the_hop_from_the_previous_show(tmp_conn):
    _save_at(tmp_conn, "s1", "2020-01-01", "v1", [_entry(1, "A")])
    _save_at(tmp_conn, "s2", "2020-01-05", "v2", [_entry(1, "A")])
    tmp_conn.execute("UPDATE venues SET latitude = 48.8566, longitude = 2.3522 WHERE id = 'v1'")
    tmp_conn.execute("UPDATE venues SET latitude = 51.5074, longitude = -0.1278 WHERE id = 'v2'")
    features.rebuild(tmp_conn)

    rows = {r["event_date"]: r["travel_km"] for r in tmp_conn.execute("SELECT event_date, travel_km FROM setlist_features")}
    assert rows["2020-01-01"] is None
    assert 340 < rows["2020-01-05"] < 347
