from undercurrents.clustering import cli
from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue
from undercurrents.storage import db


class FakeMbidClient:
    def get(self, path, params):
        return 200, {"recordings": []}


class FakeWikidataClient:
    def get(self, path, params):
        return 200, {"search": []}


class ResolvingFakeMbidClient:
    """Resolves each distinct title search to its own recording id (derived from the query
    text), then answers each one's metadata lookup — used to verify the `run` command wires
    enrichment in after title resolution, without collapsing every song into one canonical id
    (which would leave too few samples for song clustering)."""

    def get(self, path, params):
        if path.startswith("/recording/"):
            return 200, {"length": 123000, "releases": [{"date": "2015-01-01"}], "genres": []}
        mbid = f"fake-mbid-{hash(params['query']) % 10_000}"
        return 200, {"recordings": [{"id": mbid, "score": 100, "title": "whatever"}]}


SONG_NAMES = ["Elephant", "Nangs", "Eventually", "Borderline", "Breathe Deeper", "Alter Ego"]


def _seed_db(db_path, venue_country="Country"):
    conn = db.get_connection(db_path)
    db.initialize_schema(conn)
    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v1", name="V", city="C", state=None, country=venue_country)
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
    monkeypatch.setattr(cli, "WikidataClient", lambda: FakeWikidataClient())

    cli.main(["run", "--db-path", str(db_path)])

    conn = db.get_connection(db_path)
    setlist_cluster_count = conn.execute("SELECT COUNT(*) AS c FROM setlist_clusters").fetchone()["c"]
    assert setlist_cluster_count == 6
    conn.close()

    captured = capsys.readouterr()
    assert "Clustered 6 setlists" in captured.out


def test_run_command_enriches_resolved_songs_with_metadata(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    _seed_db(db_path)
    monkeypatch.setattr(cli, "MusicBrainzClient", lambda: ResolvingFakeMbidClient())
    monkeypatch.setattr(cli, "WikidataClient", lambda: FakeWikidataClient())

    cli.main(["run", "--db-path", str(db_path)])

    conn = db.get_connection(db_path)
    rows = conn.execute(
        "SELECT duration_ms, release_date FROM songs WHERE mbid LIKE 'fake-mbid-%'"
    ).fetchall()
    conn.close()

    assert len(rows) == len(SONG_NAMES)
    assert all(r["duration_ms"] == 123000 and r["release_date"] == "2015-01-01" for r in rows)


class ResolvingFakeWikidataClient:
    """Resolves the single venue used by `_seed_db` to a known capacity, used to verify the
    `run` command wires venue capacity enrichment in."""

    def get(self, path, params):
        if params.get("action") == "wbsearchentities":
            return 200, {"search": [{"id": "Q1", "label": "V", "description": "a venue"}]}
        return 200, {
            "entities": {
                "Q1": {
                    "claims": {
                        "P1083": [{"mainsnak": {"datavalue": {"value": {"amount": "+5000"}}}}],
                        "P17": [{"mainsnak": {"datavalue": {"value": {"id": "Q30"}}}}],
                    }
                }
            }
        }


def test_run_command_enriches_venue_capacity(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    _seed_db(db_path, venue_country="United States")
    monkeypatch.setattr(cli, "MusicBrainzClient", lambda: FakeMbidClient())
    monkeypatch.setattr(cli, "WikidataClient", lambda: ResolvingFakeWikidataClient())

    cli.main(["run", "--db-path", str(db_path)])

    conn = db.get_connection(db_path)
    row = conn.execute("SELECT capacity FROM venues WHERE id = 'v1'").fetchone()
    conn.close()

    assert row["capacity"] == 5000
