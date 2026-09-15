from datetime import date, timedelta

from fastapi.testclient import TestClient

from undercurrents.api.app import app
from undercurrents.api.dependencies import get_conn
from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue
from undercurrents.storage import db


def _seed(conn, n=15):
    """n setlists, 10 days apart. "Song A" plays every show (always label 1 for its own
    rows); "Song B" plays every other show (label alternates 0/1) -- keeps the shared
    classifier's combined training labels non-degenerate (both classes present), same
    reasoning as the existing prediction test fixtures. `ensure_songs_clustering_columns`
    is required before any prediction/analysis code runs -- those columns
    (`canonical_song_id`, `excluded_from_clustering`, `mbid`) aren't part of the base schema,
    only added by this migration (same convention as every existing prediction test
    fixture, e.g. `tests/test_prediction_cli.py`'s `_seed_db`)."""
    db.ensure_songs_clustering_columns(conn)
    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v1", name="Venue", city="City", state=None, country="Country A")
    start = date(2020, 1, 1)
    for i in range(n):
        songs = [SetlistSongEntry(1, 1, "Song A", False, False, None, False, None)]
        if i % 2 == 0:
            songs.append(SetlistSongEntry(2, 1, "Song B", False, False, None, False, None))
        db.save_setlist(
            conn,
            NormalizedSetlist(
                id=f"s{i}",
                event_date=(start + timedelta(days=i * 10)).isoformat(),
                last_updated_source="x",
                url=f"https://x/{i}",
                artist=artist,
                venue=venue,
                tour=None,
                songs=songs,
            ),
        )


def _client_with(conn):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_conn] = lambda: conn
    return TestClient(app)


def test_overview_returns_expected_shape(tmp_conn):
    _seed(tmp_conn)
    client = _client_with(tmp_conn)

    response = client.get("/api/stats/overview")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "concerts_logged",
        "years_start",
        "years_end",
        "venues_mapped",
        "countries",
        "setlist_clusters",
        "setlist_accuracy",
        "length_mae_songs",
    }
    assert body["concerts_logged"] == 15
    assert body["venues_mapped"] == 1
    assert body["countries"] == 1
    assert body["years_start"] == 2020
    assert body["years_end"] == 2020


def test_overview_setlist_accuracy_is_a_real_probability(tmp_conn):
    _seed(tmp_conn)
    client = _client_with(tmp_conn)

    body = client.get("/api/stats/overview").json()

    assert body["setlist_accuracy"] is not None
    assert 0.0 <= body["setlist_accuracy"] <= 1.0
    assert body["length_mae_songs"] is not None
    assert body["length_mae_songs"] >= 0.0


def test_overview_insufficient_data_returns_none_metrics(tmp_conn):
    _seed(tmp_conn, n=3)
    client = _client_with(tmp_conn)

    response = client.get("/api/stats/overview")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "concerts_logged",
        "years_start",
        "years_end",
        "venues_mapped",
        "countries",
        "setlist_clusters",
        "setlist_accuracy",
        "length_mae_songs",
    }
    assert body["setlist_accuracy"] is None
    assert body["length_mae_songs"] is None
