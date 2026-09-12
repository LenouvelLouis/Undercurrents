from undercurrents.clustering import stats
from undercurrents.storage import db
from tests.test_features import _make_setlist


def test_song_frequency_by_year_counts_per_year(tmp_conn):
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

    def make(setlist_id, year):
        artist = Artist(id="a1", name="Tame Impala", mbid="a1")
        venue = Venue(id="v1", name="V", city="C", state=None, country="Country")
        song = SetlistSongEntry(1, 1, "Elephant", False, False, None, False, None)
        return NormalizedSetlist(
            id=setlist_id, event_date=f"{year}-01-01", last_updated_source="x",
            url="https://x", artist=artist, venue=venue, tour=None, songs=[song],
        )

    db.save_setlist(tmp_conn, make("s1", 2015))
    db.save_setlist(tmp_conn, make("s2", 2015))
    db.save_setlist(tmp_conn, make("s3", 2016))

    song_id = db.get_song_id_by_name(tmp_conn, "Elephant")
    result = stats.song_frequency_by_year(tmp_conn, song_id)

    assert result == {2015: 2, 2016: 1}


def test_cluster_summary_reports_size_date_range_and_top_songs(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    _make_setlist(tmp_conn, "s1", ["Elephant", "Nangs"])
    _make_setlist(tmp_conn, "s2", ["Elephant", "Nangs"])
    _make_setlist(tmp_conn, "s3", ["Loser"])

    elephant_id = db.get_song_id_by_name(tmp_conn, "Elephant")
    nangs_id = db.get_song_id_by_name(tmp_conn, "Nangs")

    db.replace_setlist_clusters(
        tmp_conn,
        [("s1", 0.0, 0.0, 0), ("s2", 0.1, 0.1, 0), ("s3", 9.0, 9.0, 1)],
    )

    summaries = stats.cluster_summary(tmp_conn)

    cluster_0 = next(s for s in summaries if s["cluster_id"] == 0)
    assert cluster_0["size"] == 2
    assert cluster_0["date_start"] == "2019-01-01"
    assert cluster_0["date_end"] == "2019-01-01"
    assert set(cluster_0["top_song_ids"]) >= {elephant_id, nangs_id}
