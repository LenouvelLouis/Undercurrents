import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from undercurrents.ingestion.models import Artist, NormalizedSetlist, Venue

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(db_path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def initialize_schema(conn: sqlite3.Connection) -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()


def get_cached_response(conn: sqlite3.Connection, endpoint: str, params_hash: str) -> str | None:
    row = conn.execute(
        "SELECT payload_json FROM raw_responses WHERE endpoint = ? AND params_hash = ?",
        (endpoint, params_hash),
    ).fetchone()
    return row["payload_json"] if row else None


def cache_response(
    conn: sqlite3.Connection,
    endpoint: str,
    params_hash: str,
    http_status: int,
    payload_json: str,
) -> None:
    conn.execute(
        """
        INSERT INTO raw_responses (endpoint, params_hash, fetched_at, http_status, payload_json)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(endpoint, params_hash) DO UPDATE SET
            fetched_at = excluded.fetched_at,
            http_status = excluded.http_status,
            payload_json = excluded.payload_json
        """,
        (endpoint, params_hash, datetime.now(timezone.utc).isoformat(), http_status, payload_json),
    )
    conn.commit()


def upsert_artist(conn: sqlite3.Connection, artist: Artist) -> None:
    conn.execute(
        """
        INSERT INTO artists (id, name, mbid) VALUES (?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET name = excluded.name, mbid = excluded.mbid
        """,
        (artist.id, artist.name, artist.mbid),
    )


def upsert_venue(conn: sqlite3.Connection, venue: Venue) -> None:
    conn.execute(
        """
        INSERT INTO venues (id, name, city, state, country) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name, city = excluded.city,
            state = excluded.state, country = excluded.country
        """,
        (venue.id, venue.name, venue.city, venue.state, venue.country),
    )


def upsert_tour(conn: sqlite3.Connection, tour_name: str, event_year: int) -> int:
    row = conn.execute(
        "SELECT id, year_start, year_end FROM tours WHERE name = ?", (tour_name,)
    ).fetchone()
    if row is None:
        cursor = conn.execute(
            "INSERT INTO tours (name, year_start, year_end) VALUES (?, ?, ?)",
            (tour_name, event_year, event_year),
        )
        return cursor.lastrowid

    year_start = min(row["year_start"], event_year)
    year_end = max(row["year_end"], event_year)
    conn.execute(
        "UPDATE tours SET year_start = ?, year_end = ? WHERE id = ?",
        (year_start, year_end, row["id"]),
    )
    return row["id"]


def upsert_song(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute("SELECT id FROM songs WHERE name = ?", (name,)).fetchone()
    if row is not None:
        return row["id"]
    cursor = conn.execute("INSERT INTO songs (name) VALUES (?)", (name,))
    return cursor.lastrowid


def upsert_cover_artist(conn: sqlite3.Connection, name: str) -> str:
    artist_id = f"cover:{name.strip().lower()}"
    conn.execute(
        "INSERT INTO artists (id, name, mbid) VALUES (?, ?, NULL) "
        "ON CONFLICT(id) DO NOTHING",
        (artist_id, name),
    )
    return artist_id


def save_setlist(conn: sqlite3.Connection, normalized: NormalizedSetlist) -> None:
    try:
        upsert_artist(conn, normalized.artist)
        upsert_venue(conn, normalized.venue)

        tour_id = None
        if normalized.tour is not None:
            event_year = int(normalized.event_date[:4])
            tour_id = upsert_tour(conn, normalized.tour.name, event_year)

        conn.execute(
            """
            INSERT INTO setlists
                (id, event_date, tour_id, venue_id, artist_id, url, last_updated_source)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                event_date = excluded.event_date,
                tour_id = excluded.tour_id,
                venue_id = excluded.venue_id,
                artist_id = excluded.artist_id,
                url = excluded.url,
                last_updated_source = excluded.last_updated_source
            """,
            (
                normalized.id,
                normalized.event_date,
                tour_id,
                normalized.venue.id,
                normalized.artist.id,
                normalized.url,
                normalized.last_updated_source,
            ),
        )

        conn.execute("DELETE FROM setlist_songs WHERE setlist_id = ?", (normalized.id,))
        for entry in normalized.songs:
            song_id = upsert_song(conn, entry.song_name)
            cover_artist_id = (
                upsert_cover_artist(conn, entry.cover_artist_name)
                if entry.cover_artist_name
                else None
            )
            conn.execute(
                """
                INSERT INTO setlist_songs
                    (setlist_id, position, set_number, song_id, is_encore, is_cover,
                     cover_artist_id, is_tape, info)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized.id,
                    entry.position,
                    entry.set_number,
                    song_id,
                    int(entry.is_encore),
                    int(entry.is_cover),
                    cover_artist_id,
                    int(entry.is_tape),
                    entry.info,
                ),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def ensure_songs_clustering_columns(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(songs)")}
    if "mbid" not in existing:
        conn.execute("ALTER TABLE songs ADD COLUMN mbid TEXT")
    if "canonical_song_id" not in existing:
        conn.execute(
            "ALTER TABLE songs ADD COLUMN canonical_song_id INTEGER REFERENCES songs(id)"
        )
    if "excluded_from_clustering" not in existing:
        conn.execute(
            "ALTER TABLE songs ADD COLUMN excluded_from_clustering INTEGER NOT NULL DEFAULT 0"
        )
    conn.commit()


def get_unresolved_songs(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT id, name FROM songs
        WHERE mbid IS NULL AND canonical_song_id IS NULL AND excluded_from_clustering = 0
        """
    ).fetchall()


def get_song_id_by_name(conn: sqlite3.Connection, name: str) -> int | None:
    row = conn.execute("SELECT id FROM songs WHERE name = ?", (name,)).fetchone()
    return row["id"] if row else None


def rename_song(conn: sqlite3.Connection, song_id: int, new_name: str) -> None:
    conn.execute("UPDATE songs SET name = ? WHERE id = ?", (new_name, song_id))
    conn.commit()


def set_song_mbid(conn: sqlite3.Connection, song_id: int, mbid: str) -> None:
    conn.execute("UPDATE songs SET mbid = ? WHERE id = ?", (mbid, song_id))
    conn.commit()


def set_song_canonical(conn: sqlite3.Connection, song_id: int, canonical_song_id: int) -> None:
    conn.execute(
        "UPDATE songs SET canonical_song_id = ? WHERE id = ?", (canonical_song_id, song_id)
    )
    conn.commit()


def set_song_excluded(conn: sqlite3.Connection, song_id: int) -> None:
    conn.execute("UPDATE songs SET excluded_from_clustering = 1 WHERE id = ?", (song_id,))
    conn.commit()


def get_all_songs(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT id, name, mbid, canonical_song_id, excluded_from_clustering FROM songs"
    ).fetchall()


def get_setlist_song_entries(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT setlist_id, song_id FROM setlist_songs").fetchall()


def replace_setlist_clusters(
    conn: sqlite3.Connection, rows: list[tuple[str, float, float, int]]
) -> None:
    conn.execute("DELETE FROM setlist_clusters")
    conn.executemany(
        "INSERT INTO setlist_clusters (setlist_id, x, y, cluster_id) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def replace_song_clusters(
    conn: sqlite3.Connection, rows: list[tuple[int, float, float, int]]
) -> None:
    conn.execute("DELETE FROM song_clusters")
    conn.executemany(
        "INSERT INTO song_clusters (song_id, x, y, cluster_id) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
