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
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country")
    dates = [f"2020-{m:02d}-01" for m in range(1, 9)]
    cluster_rows = []
    for i, event_date in enumerate(dates):
        # 3 songs per show. "Common Song"/"Other Song" still strictly alternate (exactly one
        # of the two per show, as before -- keeps the original song-prediction model's binary
        # labels non-degenerate). "Filler Song" (always mid) and "Closer Song" (always last,
        # encore on some shows) add the position-category diversity (opener/mid/closer/encore)
        # the new position model needs -- a single-song show gives it only one class to train on.
        alternating = "Common Song" if i % 2 == 0 else "Other Song"
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
