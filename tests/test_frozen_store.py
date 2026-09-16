import json
from datetime import date, timedelta

from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue
from undercurrents.prediction.frozen_store import FrozenModelStore
from undercurrents.storage import db


def _seed(conn, n=15):
    """15 shows (> the default holdout_shows=10 used by the next-date backtest), 3 songs
    per show giving all 4 position categories (opener/mid/closer/encore), 2 alternating
    countries -- enough real signal for every one of the 5 predictors plus the backtest to
    train without hitting scikit-learn's "0 samples"/"1 class" edge cases."""
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
                event_date=(start + timedelta(days=i * 10)).isoformat(),
                last_updated_source="x",
                url=f"https://x/{i}",
                artist=artist,
                venue=venue_a if i % 2 == 0 else venue_b,
                tour=None,
                songs=songs,
            ),
        )
    conn.commit()


def test_get_next_show_model_trains_and_persists_to_disk_on_first_call(tmp_conn, tmp_path):
    _seed(tmp_conn)
    store = FrozenModelStore(models_dir=tmp_path)

    trained_model = store.get_next_show_model(tmp_conn)

    assert trained_model is not None
    assert (tmp_path / "next_show.joblib").exists()


def test_get_next_show_model_second_call_does_not_retrain(tmp_conn, tmp_path, monkeypatch):
    _seed(tmp_conn)
    store = FrozenModelStore(models_dir=tmp_path)
    first = store.get_next_show_model(tmp_conn)

    from undercurrents.prediction import features as features_module

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("should not retrain: model already cached in memory")

    monkeypatch.setattr(features_module, "build_training_rows", _fail_if_called)

    second = store.get_next_show_model(tmp_conn)

    assert second is first


def test_get_next_show_model_loads_from_disk_when_not_yet_in_memory(tmp_conn, tmp_path, monkeypatch):
    _seed(tmp_conn)
    # Populate disk via one store instance...
    FrozenModelStore(models_dir=tmp_path).get_next_show_model(tmp_conn)

    # ...then read it back with a brand new store instance (empty memory cache).
    fresh_store = FrozenModelStore(models_dir=tmp_path)

    from undercurrents.prediction import features as features_module

    def _fail_if_called(*args, **kwargs):
        raise AssertionError("should not retrain: model already present on disk")

    monkeypatch.setattr(features_module, "build_training_rows", _fail_if_called)

    loaded = fresh_store.get_next_show_model(tmp_conn)

    assert loaded is not None


def test_get_next_date_backtest_stats_trains_and_persists_to_disk(tmp_conn, tmp_path):
    _seed(tmp_conn)
    store = FrozenModelStore(models_dir=tmp_path)

    stats = store.get_next_date_backtest_stats(tmp_conn, holdout_shows=10)

    assert set(stats) == {"mae_days", "median_absolute_error_days"}
    assert (tmp_path / "next_date_backtest.json").exists()


def test_train_all_writes_every_artifact_and_metadata(tmp_conn, tmp_path):
    _seed(tmp_conn)
    store = FrozenModelStore(models_dir=tmp_path)

    result = store.train_all(tmp_conn)

    for key in [
        "next_show",
        "setlist_length",
        "position_category",
        "next_show_date",
        "next_show_country",
    ]:
        assert (tmp_path / f"{key}.joblib").exists()
    assert (tmp_path / "next_date_backtest.json").exists()
    metadata_path = tmp_path / "metadata.json"
    assert metadata_path.exists()
    metadata = json.loads(metadata_path.read_text())
    assert "trained_at" in metadata
    assert set(result["models"]) == {
        "next_show",
        "setlist_length",
        "position_category",
        "next_show_date",
        "next_show_country",
    }
    assert "mae_days" in result["backtest"]
