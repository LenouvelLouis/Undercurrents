from undercurrents.clustering import cli
from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue
from undercurrents.storage import db


class FakeMbidClient:
    def get(self, path, params):
        return 200, {"recordings": []}


SONG_NAMES = ["Elephant", "Nangs", "Eventually", "Borderline", "Breathe Deeper", "Alter Ego"]


def _seed_db(db_path):
    conn = db.get_connection(db_path)
    db.initialize_schema(conn)
    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country")
    for i in range(6):
        song = SetlistSongEntry(1, 1, SONG_NAMES[i], False, False, None, False, None)
        db.save_setlist(
            conn,
            NormalizedSetlist(
                id=f"s{i}", event_date="2019-01-01", last_updated_source="x",
                url="https://x", artist=artist, venue=venue, tour=None, songs=[song],
            ),
        )
    conn.close()


def test_run_command_populates_cluster_tables(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "test.db"
    _seed_db(db_path)
    monkeypatch.setattr(cli, "MusicBrainzClient", lambda: FakeMbidClient())

    cli.main(["run", "--db-path", str(db_path)])

    conn = db.get_connection(db_path)
    setlist_cluster_count = conn.execute("SELECT COUNT(*) AS c FROM setlist_clusters").fetchone()["c"]
    assert setlist_cluster_count == 6
    conn.close()

    captured = capsys.readouterr()
    assert "Clustered 6 setlists" in captured.out
