from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue
from undercurrents.prediction import cli
from undercurrents.storage import db


def _seed_db(db_path):
    conn = db.get_connection(db_path)
    db.initialize_schema(conn)
    db.ensure_songs_clustering_columns(conn)
    conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (1, 'Tour', 2020, 2020)")
    conn.commit()

    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue_a = Venue(id="v-a", name="V-A", city="C-A", state=None, country="Country A")
    venue_b = Venue(id="v-b", name="V-B", city="C-B", state=None, country="Country B")
    dates = [f"2020-{m:02d}-01" for m in range(1, 9)]
    cluster_rows = []
    for i, event_date in enumerate(dates):
        # 3 songs per show. "Common Song"/"Other Song" still strictly alternate (exactly one
        # of the two per show, as before -- keeps the original song-prediction model's binary
        # labels non-degenerate). "Filler Song" (always mid) and "Closer Song" (always last,
        # encore on some shows) add the position-category diversity (opener/mid/closer/encore)
        # the new position model needs -- a single-song show gives it only one class to train on.
        # The venue alternates Country A / Country B too, so the country model also sees both
        # classes.
        alternating = "Common Song" if i % 2 == 0 else "Other Song"
        venue = venue_a if i % 2 == 0 else venue_b
        songs = [
            SetlistSongEntry(1, 1, alternating, False, False, None, False, None),
            SetlistSongEntry(2, 1, "Filler Song", False, False, None, False, None),
            SetlistSongEntry(3, 1, "Closer Song", i % 3 == 0, False, None, False, None),
        ]
        db.save_setlist(
            conn,
            NormalizedSetlist(
                id=f"s{i}", event_date=event_date, last_updated_source="x",
                url=f"https://x/{i}", artist=artist, venue=venue, tour=None, songs=songs,
            ),
        )
        conn.execute("UPDATE setlists SET tour_id = 1 WHERE id = ?", (f"s{i}",))
        cluster_rows.append((f"s{i}", 0.0, 0.0, i % 2))
    conn.commit()
    db.replace_setlist_clusters(conn, cluster_rows)
    conn.close()


def test_predict_command_prints_ranked_songs(tmp_path, capsys):
    db_path = tmp_path / "test.db"
    _seed_db(db_path)

    cli.main(["predict", "--date", "2020-09-01", "--db-path", str(db_path)])

    captured = capsys.readouterr()
    assert "Common Song" in captured.out
    assert "Other Song" in captured.out
    assert "Predicted setlist length" in captured.out
    assert "Predicted position" in captured.out
    assert "Predicted next show date" in captured.out
    assert "Top 3 predicted countries" in captured.out
    assert "Country A" in captured.out or "Country B" in captured.out


def test_evaluate_command_prints_mean_accuracy(tmp_path, capsys):
    db_path = tmp_path / "test.db"
    _seed_db(db_path)

    cli.main(["evaluate", "--holdout-shows", "3", "--db-path", str(db_path)])

    captured = capsys.readouterr()
    assert "held-out shows" in captured.out
    assert "%" in captured.out
    assert "Setlist length MAE" in captured.out
    assert "Position category accuracy" in captured.out
    assert "Next show date" in captured.out
    assert "Next show country accuracy" in captured.out


def _seed_db_for_training(db_path, n=15):
    """Like `_seed_db` but with 15 shows instead of 8 -- FrozenModelStore.train_all's
    next-date backtest defaults to holdout_shows=10, which raises ValueError unless there
    are strictly more than 10 setlists (see evaluate.backtest_next_show_date's guard)."""
    from datetime import date, timedelta

    conn = db.get_connection(db_path)
    db.initialize_schema(conn)
    db.ensure_songs_clustering_columns(conn)
    conn.execute("INSERT INTO tours (id, name, year_start, year_end) VALUES (1, 'Tour', 2020, 2020)")
    conn.commit()

    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue_a = Venue(id="v-a", name="V-A", city="C-A", state=None, country="Country A")
    venue_b = Venue(id="v-b", name="V-B", city="C-B", state=None, country="Country B")
    start = date(2020, 1, 1)
    cluster_rows = []
    for i in range(n):
        event_date = (start + timedelta(days=i * 10)).isoformat()
        alternating = "Common Song" if i % 2 == 0 else "Other Song"
        venue = venue_a if i % 2 == 0 else venue_b
        songs = [
            SetlistSongEntry(1, 1, alternating, False, False, None, False, None),
            SetlistSongEntry(2, 1, "Filler Song", False, False, None, False, None),
            SetlistSongEntry(3, 1, "Closer Song", i % 3 == 0, False, None, False, None),
        ]
        db.save_setlist(
            conn,
            NormalizedSetlist(
                id=f"s{i}", event_date=event_date, last_updated_source="x",
                url=f"https://x/{i}", artist=artist, venue=venue, tour=None, songs=songs,
            ),
        )
        conn.execute("UPDATE setlists SET tour_id = 1 WHERE id = ?", (f"s{i}",))
        cluster_rows.append((f"s{i}", 0.0, 0.0, i % 2))
    conn.commit()
    db.replace_setlist_clusters(conn, cluster_rows)
    conn.close()


def test_train_models_command_writes_artifacts_and_prints_summary(tmp_path, capsys):
    db_path = tmp_path / "test.db"
    models_dir = tmp_path / "models"
    _seed_db_for_training(db_path)

    cli.main(["train-models", "--db-path", str(db_path), "--models-dir", str(models_dir)])

    for key in [
        "next_show",
        "setlist_length",
        "position_category",
        "next_show_date",
        "next_show_country",
    ]:
        assert (models_dir / f"{key}.joblib").exists()
    assert (models_dir / "next_date_backtest.json").exists()
    assert (models_dir / "metadata.json").exists()

    captured = capsys.readouterr()
    assert "Trained and saved 7 models" in captured.out
    # Without the flag the slow half must be announced as skipped rather than silently run.
    assert "--with-sequence" in captured.out
    assert "Next show date backtest" in captured.out
    assert "Trained at" in captured.out
