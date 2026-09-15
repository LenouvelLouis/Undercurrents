from fastapi.testclient import TestClient

from undercurrents.api.app import app
from undercurrents.api.dependencies import get_conn
from undercurrents.storage import db


def _client_with(conn):
    app.dependency_overrides.clear()
    app.dependency_overrides[get_conn] = lambda: conn
    return TestClient(app)


def test_list_songs_excludes_excluded_and_merged_variants(tmp_conn):
    conn = tmp_conn
    db.ensure_songs_clustering_columns(conn)  # canonical_song_id/excluded_from_clustering aren't base-schema columns
    zebra_id = db.upsert_song(conn, "Zebra Song")
    apple_id = db.upsert_song(conn, "Apple Song")
    excluded_id = db.upsert_song(conn, "Intro")
    variant_id = db.upsert_song(conn, "Apple Song (alt spelling)")
    db.set_song_excluded(conn, excluded_id)
    db.set_song_canonical(conn, variant_id, apple_id)
    conn.commit()

    client = _client_with(conn)
    response = client.get("/api/songs")

    assert response.status_code == 200
    body = response.json()
    assert [song["name"] for song in body] == ["Apple Song", "Zebra Song"]
    assert body[0]["id"] == apple_id
    assert body[1]["id"] == zebra_id
