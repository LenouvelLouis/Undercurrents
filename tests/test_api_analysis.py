from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from undercurrents.api.app import app
from undercurrents.api.dependencies import get_conn
from undercurrents.ingestion.models import (
    Artist,
    NormalizedSetlist,
    SetlistSongEntry,
    Tour,
    Venue,
)
from undercurrents.storage import db


def _client_with(conn):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_conn] = lambda: conn
    return TestClient(app)


def _setlist(conn, setlist_id, event_date, venue, songs=None):
    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    if songs is None:
        songs = [SetlistSongEntry(1, 1, "Song A", False, False, None, False, None)]
    db.save_setlist(
        conn,
        NormalizedSetlist(
            id=setlist_id,
            event_date=event_date,
            last_updated_source="x",
            url=f"https://x/{setlist_id}",
            artist=artist,
            venue=venue,
            tour=None,
            songs=songs,
        ),
    )


def test_venues_returns_show_counts_and_last_visited(tmp_conn):
    conn = tmp_conn
    venue = Venue(id="v1", name="The Venue", city="City", state=None, country="Country A")
    _setlist(conn, "s1", "2020-01-01", venue)
    _setlist(conn, "s2", "2020-02-01", venue)
    db.ensure_venues_capacity_column(conn)
    db.set_venue_capacity(conn, "v1", 5000)

    client = _client_with(conn)
    response = client.get("/api/analysis/venues")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "v1"
    assert body[0]["show_count"] == 2
    assert body[0]["last_visited"] == "2020-02-01"
    assert body[0]["capacity"] == 5000


def test_venues_capacity_is_null_when_unknown(tmp_conn):
    conn = tmp_conn
    venue = Venue(id="v1", name="The Venue", city="City", state=None, country="Country A")
    _setlist(conn, "s1", "2020-01-01", venue)

    client = _client_with(conn)
    body = client.get("/api/analysis/venues").json()

    assert body[0]["capacity"] is None


def test_setlist_trend_returns_by_year_and_eras(tmp_conn):
    conn = tmp_conn
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country A")
    _setlist(conn, "s1", "2010-01-01", venue, songs=[
        SetlistSongEntry(1, 1, "A", False, False, None, False, None),
        SetlistSongEntry(2, 1, "B", False, False, None, False, None),
    ])
    _setlist(conn, "s2", "2016-01-01", venue, songs=[
        SetlistSongEntry(1, 1, "A", False, False, None, False, None),
    ])

    client = _client_with(conn)
    response = client.get("/api/analysis/setlist-trend")

    assert response.status_code == 200
    body = response.json()
    assert body["by_year"]["2010"] == 2.0
    assert body["by_year"]["2016"] == 1.0
    era_names = [era["name"] for era in body["eras"]]
    assert era_names == ["Innerspeaker", "Lonerism", "Currents", "Slow Rush -> Deadbeat"]
    innerspeaker = body["eras"][0]
    assert innerspeaker["start_year"] == 2010  # dataset's real earliest year, not the hardcoded default
    deadbeat = body["eras"][-1]
    assert deadbeat["end_year"] == 2016  # dataset's real latest year


def _seed_two_clusters(conn):
    db.ensure_songs_clustering_columns(conn)  # db.get_all_songs (used by the detail endpoint) selects these columns
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country A")
    _setlist(conn, "s1", "2015-01-01", venue, songs=[
        SetlistSongEntry(1, 1, "Currents Song", False, False, None, False, None),
    ])
    _setlist(conn, "s2", "2015-02-01", venue, songs=[
        SetlistSongEntry(1, 1, "Currents Song", False, False, None, False, None),
    ])
    _setlist(conn, "s3", "2009-01-01", venue, songs=[
        SetlistSongEntry(1, 1, "Early Song", False, False, None, False, None),
    ])
    db.replace_setlist_clusters(
        conn,
        [("s1", 0.0, 0.0, 0), ("s2", 0.1, 0.1, 0), ("s3", 1.0, 1.0, 1)],
    )


def test_clusters_returns_one_row_per_cluster_with_dominant_period(tmp_conn):
    conn = tmp_conn
    _seed_two_clusters(conn)

    client = _client_with(conn)
    response = client.get("/api/analysis/clusters")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    cluster_0 = next(c for c in body if c["cluster_id"] == 0)
    assert cluster_0["size"] == 2
    assert cluster_0["dominant_period"] == "Currents"
    cluster_1 = next(c for c in body if c["cluster_id"] == 1)
    assert cluster_1["dominant_period"] == "Innerspeaker"


def test_cluster_detail_includes_typical_songs(tmp_conn):
    conn = tmp_conn
    _seed_two_clusters(conn)

    client = _client_with(conn)
    response = client.get("/api/analysis/clusters/0")

    assert response.status_code == 200
    body = response.json()
    assert body["cluster_id"] == 0
    assert body["size"] == 2
    song_names = [s["song_name"] for s in body["typical_songs"]]
    assert "Currents Song" in song_names


def test_cluster_detail_404s_for_unknown_cluster(tmp_conn):
    conn = tmp_conn
    _seed_two_clusters(conn)

    client = _client_with(conn)
    response = client.get("/api/analysis/clusters/999")

    assert response.status_code == 404


def test_clusters_returns_empty_list_when_no_clusters(tmp_conn):
    conn = tmp_conn
    db.ensure_songs_clustering_columns(conn)
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country A")
    _setlist(conn, "s1", "2015-01-01", venue, songs=[
        SetlistSongEntry(1, 1, "Song", False, False, None, False, None),
    ])

    client = _client_with(conn)
    response = client.get("/api/analysis/clusters")

    assert response.status_code == 200
    body = response.json()
    assert body == []


def test_cluster_detail_404s_when_no_clusters_exist(tmp_conn):
    conn = tmp_conn
    db.ensure_songs_clustering_columns(conn)
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country A")
    _setlist(conn, "s1", "2015-01-01", venue, songs=[
        SetlistSongEntry(1, 1, "Song", False, False, None, False, None),
    ])

    client = _client_with(conn)
    response = client.get("/api/analysis/clusters/0")

    assert response.status_code == 404


def _seed_transitions(conn):
    db.ensure_songs_clustering_columns(conn)  # build_song_transition_matrix filters on canonical_song_id/excluded_from_clustering
    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country A")
    # Elephant -> Feels Like We Only Go Backwards, 2 out of 2 shows.
    for i, sid in enumerate(["s1", "s2"]):
        songs = [
            SetlistSongEntry(1, 1, "Elephant", False, False, None, False, None),
            SetlistSongEntry(2, 1, "Feels Like We Only Go Backwards", False, False, None, False, None),
        ]
        db.save_setlist(
            conn,
            NormalizedSetlist(
                id=sid, event_date=f"2020-0{i + 1}-01", last_updated_source="x",
                url=f"https://x/{sid}", artist=artist, venue=venue, tour=None, songs=songs,
            ),
        )


def test_transitions_returns_ranked_follow_ons(tmp_conn):
    conn = tmp_conn
    _seed_transitions(conn)
    elephant_id = db.get_song_id_by_name(conn, "Elephant")

    client = _client_with(conn)
    response = client.get(f"/api/analysis/transitions/{elephant_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["song_name"] == "Elephant"
    assert len(body["follow_ons"]) == 1
    assert body["follow_ons"][0]["song_name"] == "Feels Like We Only Go Backwards"
    assert body["follow_ons"][0]["probability"] == 1.0


def test_transitions_returns_empty_list_for_song_with_no_follow_ons(tmp_conn):
    conn = tmp_conn
    _seed_transitions(conn)
    last_song_id = db.get_song_id_by_name(conn, "Feels Like We Only Go Backwards")

    client = _client_with(conn)
    response = client.get(f"/api/analysis/transitions/{last_song_id}")

    assert response.status_code == 200
    assert response.json()["follow_ons"] == []


def test_transitions_404s_for_unknown_song(tmp_conn):
    conn = tmp_conn
    _seed_transitions(conn)

    client = _client_with(conn)
    response = client.get("/api/analysis/transitions/999999")

    assert response.status_code == 404


def _seed_anecdotes(conn):
    """Info text must contain the exact keywords `clustering.annotations` matches on
    (`clustering/annotations.py`'s `SONG_DEBUT_KEYWORDS = ["debut"]` and
    `SETLIST_DISRUPTED_KEYWORDS = [..., "cut short", ...]`) -- these are plain substring
    checks, not fuzzy matching, so the seed text below must literally contain "debut" /
    "cut short" for the flags to actually come back True."""
    db.ensure_songs_clustering_columns(conn)  # the anecdotes endpoint's db.get_all_songs call needs these columns
    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country A")
    debut_song = SetlistSongEntry(
        1, 1, "Dracula", False, False, None, False, "Live debut of this song tonight"
    )
    db.save_setlist(
        conn,
        NormalizedSetlist(
            id="s1", event_date="2026-03-14", last_updated_source="x", url="https://x/1",
            artist=artist, venue=venue, tour=None, songs=[debut_song],
        ),
    )
    disrupted = NormalizedSetlist(
        id="s2", event_date="2025-11-02", last_updated_source="x", url="https://x/2",
        artist=artist, venue=venue, tour=None,
        songs=[SetlistSongEntry(1, 1, "Elephant", False, False, None, False, None)],
        info="Show cut short due to a medical incident",
    )
    db.save_setlist(conn, disrupted)


def test_anecdotes_returns_tagged_timeline_sorted_newest_first(tmp_conn):
    conn = tmp_conn
    _seed_anecdotes(conn)

    client = _client_with(conn)
    response = client.get("/api/analysis/anecdotes")

    assert response.status_code == 200
    body = response.json()
    dates = [entry["date"] for entry in body]
    assert dates == sorted(dates, reverse=True)
    tags = {entry["tag"] for entry in body}
    assert "song debut" in tags
    assert "disrupted show" in tags


def test_anecdotes_respects_limit(tmp_conn):
    conn = tmp_conn
    _seed_anecdotes(conn)

    client = _client_with(conn)
    response = client.get("/api/analysis/anecdotes?limit=1")

    assert len(response.json()) == 1


# Unit tests for pure helper functions (no HTTP, no DB)
from undercurrents.api.analysis import _compute_milestones, _build_anecdotes


def test_compute_milestones_100th_show_triggers_milestone():
    """Verify that every 100th show gets a milestone entry."""
    from datetime import date, timedelta
    start = date(2020, 1, 1)
    shows = [
        {
            "id": f"s{i}",
            "event_date": (start + timedelta(days=i)).isoformat(),
            "length": 10 + i % 5,
        }
        for i in range(100)
    ]

    milestones = _compute_milestones(shows)

    descriptions = [m["description"] for m in milestones]
    assert any("100th logged concert" in d for d in descriptions)


def test_compute_milestones_equal_lengths_only_first_triggers_longest():
    """Verify that when two consecutive shows have equal length, only the first one
    (the one with the previous maximum) triggers a 'longest setlist' milestone."""
    shows = [
        {"id": "s1", "event_date": "2020-01-01", "length": 10},
        {"id": "s2", "event_date": "2020-01-02", "length": 15},  # longest so far
        {"id": "s3", "event_date": "2020-01-03", "length": 15},  # equal length, should NOT trigger
        {"id": "s4", "event_date": "2020-01-04", "length": 12},
    ]

    milestones = _compute_milestones(shows)

    longest_descriptions = [m["description"] for m in milestones if "Longest setlist" in m["description"]]
    assert len(longest_descriptions) == 1
    assert "15 songs" in longest_descriptions[0]
    assert any("2020-01-02" == m["date"] for m in milestones if "15 songs" in m["description"])


def test_build_anecdotes_with_empty_inputs_returns_empty_list():
    """Verify that _build_anecdotes returns an empty list when given empty inputs."""
    result = _build_anecdotes([], [], {}, {}, [])

    assert result == []


# ---------------------------------------------------------------------------
# Tours, covers, encores, the song map and cities
# ---------------------------------------------------------------------------


def _setlist_with(conn, setlist_id, event_date, venue, songs, tour=None):
    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    db.save_setlist(
        conn,
        NormalizedSetlist(
            id=setlist_id,
            event_date=event_date,
            last_updated_source="x",
            url=f"https://x/{setlist_id}",
            artist=artist,
            venue=venue,
            tour=tour,
            songs=songs,
        ),
    )


def test_tours_counts_shows_venues_and_countries(tmp_conn):
    conn = tmp_conn
    v1 = Venue(id="v1", name="Venue One", city="Paris", state=None, country="France")
    v2 = Venue(id="v2", name="Venue Two", city="Berlin", state=None, country="Germany")
    two_songs = [
        SetlistSongEntry(1, 1, "Song A", False, False, None, False, None),
        SetlistSongEntry(2, 1, "Song B", False, False, None, False, None),
    ]
    one_song = [SetlistSongEntry(1, 1, "Song A", False, False, None, False, None)]
    _setlist_with(conn, "s1", "2015-04-08", v1, two_songs, tour=Tour(name="Currents"))
    _setlist_with(conn, "s2", "2016-06-01", v2, two_songs, tour=Tour(name="Currents"))
    _setlist_with(conn, "s3", "2012-08-11", v1, one_song, tour=Tour(name="Lonerism"))

    client = _client_with(conn)
    response = client.get("/api/analysis/tours")

    assert response.status_code == 200
    body = response.json()
    by_name = {t["name"]: t for t in body}
    assert by_name["Currents"]["show_count"] == 2
    assert by_name["Currents"]["venue_count"] == 2
    assert by_name["Currents"]["country_count"] == 2
    assert by_name["Currents"]["date_start"] == "2015-04-08"
    assert by_name["Currents"]["date_end"] == "2016-06-01"
    assert by_name["Currents"]["avg_songs"] == 2.0
    assert by_name["Lonerism"]["show_count"] == 1
    # oldest tour first
    assert body[0]["name"] == "Lonerism"


def test_tours_excludes_tape_entries_from_average(tmp_conn):
    conn = tmp_conn
    venue = Venue(id="v1", name="Venue", city="City", state=None, country="Country A")
    songs = [
        SetlistSongEntry(1, 1, "Intro Tape", False, False, None, True, None),
        SetlistSongEntry(2, 1, "Song A", False, False, None, False, None),
    ]
    _setlist_with(conn, "s1", "2020-01-01", venue, songs, tour=Tour(name="The Slow Rush"))

    body = _client_with(conn).get("/api/analysis/tours").json()
    assert body[0]["avg_songs"] == 1.0


def test_covers_group_by_artist_with_their_songs(tmp_conn):
    conn = tmp_conn
    venue = Venue(id="v1", name="Venue", city="City", state=None, country="Country A")
    songs = [
        SetlistSongEntry(1, 1, "Remember Me", False, True, "Blue Boy", False, None),
        SetlistSongEntry(2, 1, "Own Song", False, False, None, False, None),
    ]
    _setlist_with(conn, "s1", "2019-01-01", venue, songs)
    _setlist_with(conn, "s2", "2020-01-01", venue, songs)

    body = _client_with(conn).get("/api/analysis/covers").json()

    assert len(body) == 1
    entry = body[0]
    assert entry["artist_name"] == "Blue Boy"
    assert entry["play_count"] == 2
    assert entry["song_count"] == 1
    assert entry["first_played"] == "2019-01-01"
    assert entry["last_played"] == "2020-01-01"
    assert entry["songs"] == [{"song_name": "Remember Me", "play_count": 2}]


def test_covers_is_empty_when_nothing_was_covered(tmp_conn):
    conn = tmp_conn
    venue = Venue(id="v1", name="Venue", city="City", state=None, country="Country A")
    _setlist_with(
        conn, "s1", "2020-01-01", venue,
        [SetlistSongEntry(1, 1, "Song A", False, False, None, False, None)],
    )
    assert _client_with(conn).get("/api/analysis/covers").json() == []


def test_encores_rank_songs_and_report_the_rate(tmp_conn):
    conn = tmp_conn
    venue = Venue(id="v1", name="Venue", city="City", state=None, country="Country A")
    with_encore = [
        SetlistSongEntry(1, 1, "Opener", False, False, None, False, None),
        SetlistSongEntry(2, 2, "Closer", True, False, None, False, None),
    ]
    without = [SetlistSongEntry(1, 1, "Opener", False, False, None, False, None)]
    _setlist_with(conn, "s1", "2020-01-01", venue, with_encore)
    _setlist_with(conn, "s2", "2020-02-01", venue, with_encore)
    _setlist_with(conn, "s3", "2020-03-01", venue, without)

    body = _client_with(conn).get("/api/analysis/encores").json()

    assert body["shows_with_encore"] == 2
    assert body["shows_total"] == 3
    assert body["encore_entries"] == 2
    assert body["encore_rate"] == pytest.approx(2 / 3, abs=1e-4)
    assert body["songs"][0] == {
        "song_id": body["songs"][0]["song_id"],
        "song_name": "Closer",
        "encore_count": 2,
    }


def test_song_map_returns_stored_coordinates_and_play_counts(tmp_conn):
    conn = tmp_conn
    venue = Venue(id="v1", name="Venue", city="City", state=None, country="Country A")
    _setlist_with(
        conn, "s1", "2020-01-01", venue,
        [SetlistSongEntry(1, 1, "Song A", False, False, None, False, None)],
    )
    _setlist_with(
        conn, "s2", "2020-02-01", venue,
        [SetlistSongEntry(1, 1, "Song A", False, False, None, False, None)],
    )
    song_id = db.get_song_id_by_name(conn, "Song A")
    db.replace_song_clusters(conn, [(song_id, 1.5, -2.25, 3)])

    body = _client_with(conn).get("/api/analysis/song-map").json()

    assert len(body) == 1
    assert body[0]["song_name"] == "Song A"
    assert body[0]["x"] == 1.5
    assert body[0]["y"] == -2.25
    assert body[0]["cluster_id"] == 3
    assert body[0]["play_count"] == 2


def test_cities_aggregate_venues_in_the_same_city(tmp_conn):
    conn = tmp_conn
    v1 = Venue(id="v1", name="Room One", city="Paris", state=None, country="France")
    v2 = Venue(id="v2", name="Room Two", city="Paris", state=None, country="France")
    v3 = Venue(id="v3", name="Room Three", city="Berlin", state=None, country="Germany")
    song = [SetlistSongEntry(1, 1, "Song A", False, False, None, False, None)]
    _setlist_with(conn, "s1", "2020-01-01", v1, song)
    _setlist_with(conn, "s2", "2021-01-01", v2, song)
    _setlist_with(conn, "s3", "2022-01-01", v3, song)

    body = _client_with(conn).get("/api/analysis/cities").json()

    assert body[0]["city"] == "Paris"
    assert body[0]["show_count"] == 2
    assert body[0]["venue_count"] == 2
    assert body[0]["last_visited"] == "2021-01-01"
    assert body[1]["city"] == "Berlin"
    assert body[1]["venue_count"] == 1
