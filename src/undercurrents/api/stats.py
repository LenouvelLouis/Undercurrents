from fastapi import APIRouter, Depends

from undercurrents.api.dependencies import get_conn

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/overview")
def get_overview(conn=Depends(get_conn)):
    concerts_row = conn.execute(
        "SELECT COUNT(*) AS c, MIN(event_date) AS min_d, MAX(event_date) AS max_d FROM setlists"
    ).fetchone()
    venues_row = conn.execute("SELECT COUNT(*) AS c FROM venues").fetchone()
    countries_row = conn.execute(
        "SELECT COUNT(DISTINCT country) AS c FROM venues WHERE country IS NOT NULL"
    ).fetchone()
    clusters_row = conn.execute(
        "SELECT COUNT(DISTINCT cluster_id) AS c FROM setlist_clusters"
    ).fetchone()

    return {
        "concerts_logged": concerts_row["c"],
        "years_start": int(concerts_row["min_d"][:4]) if concerts_row["min_d"] else None,
        "years_end": int(concerts_row["max_d"][:4]) if concerts_row["max_d"] else None,
        "venues_mapped": venues_row["c"],
        "countries": countries_row["c"],
        "setlist_clusters": clusters_row["c"],
    }
