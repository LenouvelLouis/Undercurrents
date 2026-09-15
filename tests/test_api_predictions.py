from datetime import date, timedelta

from fastapi.testclient import TestClient

from undercurrents.api.app import app
from undercurrents.api.dependencies import get_conn
from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue
from undercurrents.storage import db


def _seed(conn, n=15):
    """Same fixture as Task 1's `_seed` -- `ensure_songs_clustering_columns` is required
    before `predict_next_show`/`predict_setlist_length` run (they read/filter on
    `songs.canonical_song_id` / `excluded_from_clustering`, only added by this migration,
    not part of the base schema)."""
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


def test_next_setlist_returns_ranked_songs(tmp_conn):
    _seed(tmp_conn)
    client = _client_with(tmp_conn)

    response = client.get("/api/predictions/next-setlist")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    names = {row["song_name"] for row in body}
    assert names == {"Song A", "Song B"}
    probabilities = [row["probability"] for row in body]
    assert probabilities == sorted(probabilities, reverse=True)
    assert body[0]["song_name"] == "Song A"  # plays every show, should rank first


def test_setlist_length_returns_a_float(tmp_conn):
    _seed(tmp_conn)
    client = _client_with(tmp_conn)

    response = client.get("/api/predictions/setlist-length")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"predicted_songs"}
    assert body["predicted_songs"] > 0


def test_next_setlist_returns_503_on_empty_database(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    client = _client_with(tmp_conn)

    response = client.get("/api/predictions/next-setlist")

    assert response.status_code == 503
    body = response.json()
    assert body["detail"] == "Not enough data to generate a prediction yet"


def test_setlist_length_returns_503_on_empty_database(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    client = _client_with(tmp_conn)

    response = client.get("/api/predictions/setlist-length")

    assert response.status_code == 503
    body = response.json()
    assert body["detail"] == "Not enough data to generate a prediction yet"


def _seed_with_roles_and_countries(conn, n=20):
    """3 songs per show: "Opener Song" always position 1 (category "opener"), "Mid Song"
    always position 2 (category "mid"), and a 3rd, last-position song that alternates
    between a non-encore "Closer Song" (category "closer") and an encore "Encore Song"
    (category "encore") -- gives the position-category model all 4 categories to train on
    (all-4-present is required: `position.predict_proba` only returns keys for classes the
    model actually saw during training, per `model.classes_`). Venue alternates two
    countries so the country model also has 2 classes."""
    db.ensure_songs_clustering_columns(conn)
    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue_a = Venue(id="v-a", name="V-A", city="C-A", state=None, country="Country A")
    venue_b = Venue(id="v-b", name="V-B", city="C-B", state=None, country="Country B")
    start = date(2020, 1, 1)
    for i in range(n):
        third_song = (
            SetlistSongEntry(3, 1, "Closer Song", False, False, None, False, None)
            if i % 2 == 0
            else SetlistSongEntry(3, 1, "Encore Song", True, False, None, False, None)
        )
        songs = [
            SetlistSongEntry(1, 1, "Opener Song", False, False, None, False, None),
            SetlistSongEntry(2, 1, "Mid Song", False, False, None, False, None),
            third_song,
        ]
        db.save_setlist(
            conn,
            NormalizedSetlist(
                id=f"s{i}",
                event_date=(start + timedelta(days=i * 7)).isoformat(),
                last_updated_source="x",
                url=f"https://x/{i}",
                artist=artist,
                venue=venue_a if i % 2 == 0 else venue_b,
                tour=None,
                songs=songs,
            ),
        )


def test_song_role_returns_probabilities_for_all_four_categories(tmp_conn):
    _seed_with_roles_and_countries(tmp_conn)
    opener_id = db.get_song_id_by_name(tmp_conn, "Opener Song")
    client = _client_with(tmp_conn)

    response = client.get(f"/api/predictions/song-role/{opener_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["song_id"] == opener_id
    assert body["song_name"] == "Opener Song"
    assert set(body["probabilities"]) == {"opener", "mid", "closer", "encore"}
    assert abs(sum(body["probabilities"].values()) - 1.0) < 1e-6


def test_song_role_404s_for_unknown_song(tmp_conn):
    _seed_with_roles_and_countries(tmp_conn)
    client = _client_with(tmp_conn)

    response = client.get("/api/predictions/song-role/999999")

    assert response.status_code == 404


def test_next_date_returns_predicted_date_and_error_stats(tmp_conn):
    _seed_with_roles_and_countries(tmp_conn)
    client = _client_with(tmp_conn)

    response = client.get("/api/predictions/next-date")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "predicted_date",
        "days_from_today",
        "mae_days",
        "median_absolute_error_days",
    }
    assert body["mae_days"] >= 0.0
    assert body["median_absolute_error_days"] >= 0.0


def test_next_country_returns_ranked_countries(tmp_conn):
    _seed_with_roles_and_countries(tmp_conn)
    client = _client_with(tmp_conn)

    response = client.get("/api/predictions/next-country")

    assert response.status_code == 200
    body = response.json()
    assert {row["country"] for row in body} == {"Country A", "Country B"}
    probabilities = [row["probability"] for row in body]
    assert probabilities == sorted(probabilities, reverse=True)


def test_song_role_returns_503_on_empty_database(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    # Create at least one song so the 404 check passes; training will fail due to no position data
    song_id = db.upsert_song(tmp_conn, "Test Song")
    client = _client_with(tmp_conn)

    response = client.get(f"/api/predictions/song-role/{song_id}")

    assert response.status_code == 503
    body = response.json()
    assert body["detail"] == "Not enough data to generate a prediction yet"


def test_next_date_returns_503_on_empty_database(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    client = _client_with(tmp_conn)

    response = client.get("/api/predictions/next-date")

    assert response.status_code == 503
    body = response.json()
    assert body["detail"] == "Not enough data to generate a prediction yet"


def test_next_country_returns_503_on_empty_database(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    client = _client_with(tmp_conn)

    response = client.get("/api/predictions/next-country")

    assert response.status_code == 503
    body = response.json()
    assert body["detail"] == "Not enough data to generate a prediction yet"


def test_predictions_endpoint_works_with_fresh_schema_when_ensure_called(tmp_conn):
    """Regression test: verify that GET /api/predictions/next-setlist works on a
    fresh database when ensure_songs_clustering_columns is called (the actual behavior
    after the fix to get_conn() that centralizes this call in the dependency injection
    layer). This prevents a crash when the endpoint is called on a database that never
    had ensure_songs_clustering_columns run manually -- the prior bug was that routes
    calling db.get_all_songs() would crash with "no such column: mbid" on such a fresh DB."""

    # Seed one setlist WITHOUT manually calling ensure_songs_clustering_columns
    # (unlike _seed which calls it first)
    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v1", name="Venue", city="City", state=None, country="Country A")
    songs = [SetlistSongEntry(1, 1, "Song A", False, False, None, False, None)]
    db.save_setlist(
        tmp_conn,
        NormalizedSetlist(
            id="s1",
            event_date="2020-01-01",
            last_updated_source="x",
            url="https://x/1",
            artist=artist,
            venue=venue,
            tour=None,
            songs=songs,
        ),
    )

    # Create a dependency override that mimics the fixed get_conn() behavior:
    # calling ensure_songs_clustering_columns before yielding the connection
    def get_conn_with_ensure():
        db.ensure_songs_clustering_columns(tmp_conn)
        yield tmp_conn

    app.dependency_overrides.clear()
    app.dependency_overrides[get_conn] = get_conn_with_ensure
    client = TestClient(app)

    # Should not crash -- the centralized ensure call handles the missing columns.
    # With only 1 show, should get a 503 (not enough data) rather than a 500 crash.
    response = client.get("/api/predictions/next-setlist")

    assert response.status_code == 503
    assert response.json()["detail"] == "Not enough data to generate a prediction yet"
