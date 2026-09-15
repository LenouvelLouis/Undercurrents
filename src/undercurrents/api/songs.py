from fastapi import APIRouter, Depends

from undercurrents.api.dependencies import get_conn
from undercurrents.storage import db

router = APIRouter(prefix="/api/songs", tags=["songs"])


@router.get("")
def list_songs(conn=Depends(get_conn)):
    db.ensure_songs_clustering_columns(conn)
    rows = conn.execute(
        """
        SELECT id, name FROM songs
        WHERE canonical_song_id IS NULL AND excluded_from_clustering = 0
        ORDER BY name
        """
    ).fetchall()
    return [{"id": row["id"], "name": row["name"]} for row in rows]
