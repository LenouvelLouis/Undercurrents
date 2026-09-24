from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from undercurrents.api import predictions as predictions_api
from undercurrents.api.app import app
from undercurrents.api.dependencies import get_conn
from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue
from undercurrents.prediction import replay
from undercurrents.storage import db


def _seed(conn, n=40):
    """A always plays, B every other show, C every third show, D once at show 30 (a debut)."""
    db.ensure_songs_clustering_columns(conn)
    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v1", name="Venue", city="City", state=None, country="Country A")
    start = date(2020, 1, 1)
    for i in range(n):
        names = ["Song A"]
        if i % 2 == 0:
            names.append("Song B")
        if i % 3 == 0:
            names.append("Song C")
        if i == 30:
            names.append("Song D")
        songs = [SetlistSongEntry(p + 1, 1, name, False, False, None, False, None) for p, name in enumerate(names)]
        db.save_setlist(
            conn,
            NormalizedSetlist(
                id=f"s{i}",
                event_date=(start + timedelta(days=i * 5)).isoformat(),
                last_updated_source="x",
                url=f"https://x/{i}",
                artist=artist,
                venue=venue,
                tour=None,
                songs=songs,
            ),
        )


def test_replay_scores_only_after_warm_up_and_never_on_future_shows(tmp_conn):
    _seed(tmp_conn)
    result = replay.backtest(tmp_conn, refit_every=5, min_train_shows=10)

    assert result["shows_scored"] == 30
    first = result["shows"][0]
    assert first["setlist_id"] == "s10"
    # trained strictly before the scored show
    for show in result["shows"]:
        assert show["trained_through"] < show["event_date"]
        assert 0.0 <= show["accuracy"] <= 1.0
    debut_night = next(s for s in result["shows"] if s["setlist_id"] == "s30")
    song_d = tmp_conn.execute("SELECT id FROM songs WHERE name = 'Song D'").fetchone()["id"]
    assert debut_night["unseen_songs"] == [song_d]
    assert sum(b["count"] for b in result["calibration"]) > 0


def test_replay_refuses_a_tiny_archive(tmp_conn):
    _seed(tmp_conn, n=8)
    with pytest.raises(ValueError):
        replay.backtest(tmp_conn, min_train_shows=10)


@pytest.fixture
def client(tmp_conn, tmp_path, monkeypatch):
    _seed(tmp_conn)
    monkeypatch.setattr(predictions_api.store, "models_dir", tmp_path)
    predictions_api.store._cache.clear()
    monkeypatch.setattr(replay, "MIN_TRAIN_SHOWS", 10)
    monkeypatch.setattr(replay.backtest, "__defaults__", (5, 10))
    app.dependency_overrides.clear()
    app.dependency_overrides[get_conn] = lambda: tmp_conn
    yield TestClient(app)
    app.dependency_overrides.clear()
    predictions_api.store._cache.clear()


def test_show_list_and_detail(client):
    shows = client.get("/api/shows").json()
    assert len(shows) == 40
    assert shows[0]["id"] == "s39"  # newest first
    assert shows[-1]["replay_accuracy"] is None  # inside the warm-up

    detail = client.get("/api/shows/s30").json()
    names = [s["name"] for s in detail["songs"]]
    assert "Song D" in names
    song_d = next(s for s in detail["songs"] if s["name"] == "Song D")
    assert song_d["rarity"]["first_time"] is True
    assert song_d["predicted_probability"] is None
    assert detail["replay"]["unseen_songs"] == ["Song D"]
    assert detail["previous_id"] == "s29" and detail["next_id"] == "s31"


def test_unknown_show_is_404(client):
    assert client.get("/api/shows/nope").status_code == 404
