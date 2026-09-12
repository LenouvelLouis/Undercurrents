import sqlite3

import pytest


def test_initialize_schema_creates_expected_tables(tmp_path):
    from undercurrents.storage import db

    conn = db.get_connection(tmp_path / "test.db")
    db.initialize_schema(conn)

    tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {
        "raw_responses",
        "artists",
        "tours",
        "venues",
        "setlists",
        "songs",
        "setlist_songs",
    } <= tables
    conn.close()


def test_initialize_schema_is_idempotent_on_an_existing_db_file(tmp_path):
    from undercurrents.storage import db

    db_path = tmp_path / "test.db"

    conn = db.get_connection(db_path)
    db.initialize_schema(conn)
    conn.close()

    # Simulates re-running the CLI's `fetch` command against the same --db-path,
    # a fresh connection to a file that already has the schema applied.
    conn = db.get_connection(db_path)
    db.initialize_schema(conn)
    conn.close()


def test_foreign_keys_are_enforced(tmp_conn):
    with pytest.raises(sqlite3.IntegrityError):
        tmp_conn.execute(
            "INSERT INTO setlist_songs "
            "(setlist_id, position, set_number, song_id) VALUES (?, ?, ?, ?)",
            ("nonexistent-setlist", 1, 1, 999),
        )


def test_cache_response_and_get_cached_response_roundtrip(tmp_conn):
    from undercurrents.storage import db

    db.cache_response(tmp_conn, "/foo", "hash1", 200, '{"a": 1}')
    result = db.get_cached_response(tmp_conn, "/foo", "hash1")
    assert result == '{"a": 1}'


def test_get_cached_response_returns_none_when_absent(tmp_conn):
    from undercurrents.storage import db

    assert db.get_cached_response(tmp_conn, "/foo", "missing") is None


def test_cache_response_upserts_on_conflict(tmp_conn):
    from undercurrents.storage import db

    db.cache_response(tmp_conn, "/foo", "hash1", 200, '{"a": 1}')
    db.cache_response(tmp_conn, "/foo", "hash1", 200, '{"a": 2}')

    count = tmp_conn.execute("SELECT COUNT(*) AS c FROM raw_responses").fetchone()["c"]
    assert count == 1
    assert db.get_cached_response(tmp_conn, "/foo", "hash1") == '{"a": 2}'


def test_upsert_tour_creates_then_expands_year_range(tmp_conn):
    from undercurrents.storage import db

    tour_id_1 = db.upsert_tour(tmp_conn, "Currents Tour", 2015)
    tour_id_2 = db.upsert_tour(tmp_conn, "Currents Tour", 2016)

    assert tour_id_1 == tour_id_2
    row = tmp_conn.execute(
        "SELECT year_start, year_end FROM tours WHERE id = ?", (tour_id_1,)
    ).fetchone()
    assert row["year_start"] == 2015
    assert row["year_end"] == 2016


def test_upsert_song_dedupes_by_name(tmp_conn):
    from undercurrents.storage import db

    id1 = db.upsert_song(tmp_conn, "Elephant")
    id2 = db.upsert_song(tmp_conn, "Elephant")
    assert id1 == id2


def test_save_setlist_stores_songs_in_order(tmp_conn):
    from undercurrents.storage import db
    from undercurrents.ingestion.normalize import normalize_setlist
    from undercurrents.ingestion.raw_schema import RawSetlist
    from tests.helpers import make_raw_setlist_dict

    normalized = normalize_setlist(
        RawSetlist.model_validate(
            make_raw_setlist_dict(songs=[{"name": "Let It Happen"}, {"name": "Elephant"}])
        )
    )
    db.save_setlist(tmp_conn, normalized)

    rows = tmp_conn.execute(
        "SELECT position FROM setlist_songs WHERE setlist_id = ? ORDER BY position",
        (normalized.id,),
    ).fetchall()
    assert [r["position"] for r in rows] == [1, 2]


def test_save_setlist_is_idempotent(tmp_conn):
    from undercurrents.storage import db
    from undercurrents.ingestion.normalize import normalize_setlist
    from undercurrents.ingestion.raw_schema import RawSetlist
    from tests.helpers import make_raw_setlist_dict

    normalized = normalize_setlist(
        RawSetlist.model_validate(
            make_raw_setlist_dict(songs=[{"name": "Let It Happen"}, {"name": "Elephant"}])
        )
    )
    db.save_setlist(tmp_conn, normalized)
    db.save_setlist(tmp_conn, normalized)

    song_count = tmp_conn.execute(
        "SELECT COUNT(*) AS c FROM setlist_songs WHERE setlist_id = ?", (normalized.id,)
    ).fetchone()["c"]
    assert song_count == 2

    setlist_count = tmp_conn.execute("SELECT COUNT(*) AS c FROM setlists").fetchone()["c"]
    assert setlist_count == 1


def test_save_setlist_stores_cover_song_with_cover_artist(tmp_conn):
    from undercurrents.storage import db
    from undercurrents.ingestion.normalize import normalize_setlist
    from undercurrents.ingestion.raw_schema import RawSetlist
    from tests.helpers import make_raw_setlist_dict

    normalized = normalize_setlist(
        RawSetlist.model_validate(
            make_raw_setlist_dict(
                songs=[{"name": "Adventure of a Lifetime", "cover": {"name": "Coldplay"}}]
            )
        )
    )
    db.save_setlist(tmp_conn, normalized)

    row = tmp_conn.execute(
        "SELECT is_cover, cover_artist_id FROM setlist_songs WHERE setlist_id = ?",
        (normalized.id,),
    ).fetchone()
    assert row["is_cover"] == 1
    assert row["cover_artist_id"] == "cover:coldplay"

    cover_artist = tmp_conn.execute(
        "SELECT name FROM artists WHERE id = ?", ("cover:coldplay",)
    ).fetchone()
    assert cover_artist["name"] == "Coldplay"


def test_save_setlist_rolls_back_on_failure(tmp_conn):
    from dataclasses import replace

    from undercurrents.storage import db
    from undercurrents.ingestion.normalize import normalize_setlist
    from undercurrents.ingestion.raw_schema import RawSetlist
    from tests.helpers import make_raw_setlist_dict

    normalized = normalize_setlist(
        RawSetlist.model_validate(make_raw_setlist_dict(setlist_id="broken-setlist"))
    )
    # Corrupt the event_date so `int(event_date[:4])` inside save_setlist raises ValueError,
    # partway through (after the artist/venue upserts, before the setlist row is written).
    broken = replace(normalized, event_date="invalid-date")

    with pytest.raises(ValueError):
        db.save_setlist(tmp_conn, broken)

    # Nothing from the failed attempt should have been committed.
    setlist_row = tmp_conn.execute(
        "SELECT 1 FROM setlists WHERE id = ?", ("broken-setlist",)
    ).fetchone()
    assert setlist_row is None

    # A subsequent successful save on a fresh connection state should still work cleanly.
    db.save_setlist(tmp_conn, normalized)
    count = tmp_conn.execute("SELECT COUNT(*) AS c FROM setlists").fetchone()["c"]
    assert count == 1
