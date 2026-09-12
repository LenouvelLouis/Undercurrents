from undercurrents.clustering import enrichment
from undercurrents.clustering.mbid_client import MusicBrainzError
from undercurrents.storage import db


class FakeMbidClient:
    def __init__(self, responses_by_mbid: dict):
        self._responses = responses_by_mbid
        self.calls = []

    def get(self, path, params):
        self.calls.append((path, dict(params)))
        for mbid, payload in self._responses.items():
            if path == f"/recording/{mbid}":
                return 200, payload
        return 200, {}


def _seed_resolved_song(conn, name, mbid):
    song_id = db.upsert_song(conn, name)
    conn.commit()
    db.ensure_songs_clustering_columns(conn)
    db.set_song_mbid(conn, song_id, mbid)
    return song_id


def test_enrich_song_metadata_sets_duration_release_date_and_genres(tmp_conn):
    song_id = _seed_resolved_song(tmp_conn, "Elephant", "mbid-1")
    client = FakeMbidClient(
        {
            "mbid-1": {
                "length": 275000,
                "releases": [{"date": "2012-10-05"}, {"date": "2022-01-01"}],
                "genres": [{"name": "psychedelic rock"}, {"name": "neo-psychedelia"}],
            }
        }
    )

    enrichment.enrich_song_metadata(tmp_conn, client)

    row = tmp_conn.execute(
        "SELECT release_date, duration_ms, genre_tags FROM songs WHERE id = ?", (song_id,)
    ).fetchone()
    assert row["duration_ms"] == 275000
    assert row["release_date"] == "2012-10-05"  # earliest of the two release dates
    assert row["genre_tags"] == '["psychedelic rock", "neo-psychedelia"]'


def test_enrich_song_metadata_falls_back_to_tags_when_no_genres(tmp_conn):
    song_id = _seed_resolved_song(tmp_conn, "Elephant", "mbid-1")
    client = FakeMbidClient(
        {"mbid-1": {"length": 275000, "releases": [], "tags": [{"name": "psychedelic"}]}}
    )

    enrichment.enrich_song_metadata(tmp_conn, client)

    row = tmp_conn.execute("SELECT genre_tags FROM songs WHERE id = ?", (song_id,)).fetchone()
    assert row["genre_tags"] == '["psychedelic"]'


def test_enrich_song_metadata_handles_missing_length_and_releases(tmp_conn):
    song_id = _seed_resolved_song(tmp_conn, "Elephant", "mbid-1")
    client = FakeMbidClient({"mbid-1": {"releases": [], "genres": []}})

    enrichment.enrich_song_metadata(tmp_conn, client)

    row = tmp_conn.execute(
        "SELECT release_date, duration_ms, genre_tags FROM songs WHERE id = ?", (song_id,)
    ).fetchone()
    assert row["duration_ms"] is None
    assert row["release_date"] is None
    assert row["genre_tags"] == "[]"


def test_enrich_song_metadata_skips_unresolved_songs(tmp_conn):
    db.ensure_songs_clustering_columns(tmp_conn)
    db.upsert_song(tmp_conn, "Unresolved Song")
    tmp_conn.commit()
    client = FakeMbidClient({})

    enrichment.enrich_song_metadata(tmp_conn, client)

    assert client.calls == []


def test_enrich_song_metadata_does_not_requery_already_enriched_song(tmp_conn):
    song_id = _seed_resolved_song(tmp_conn, "Elephant", "mbid-1")
    client = FakeMbidClient({"mbid-1": {"length": 275000, "releases": [], "genres": []}})

    enrichment.enrich_song_metadata(tmp_conn, client)
    enrichment.enrich_song_metadata(tmp_conn, client)

    assert len(client.calls) == 1


def test_enrich_song_metadata_finds_earlier_date_via_linked_work(tmp_conn):
    song_id = _seed_resolved_song(tmp_conn, "Apocalypse Dreams", "mbid-1")
    client = FakeMbidClient(
        {
            "mbid-1": {
                "length": 471775,
                "releases": [{"date": "2022-01-01"}],  # a later remaster, resolved by search
                "genres": [],
                "relations": [{"target-type": "work", "work": {"id": "work-1"}}],
            }
        }
    )
    client._responses["work-1"] = None  # placeholder, handled via get() override below

    def get(path, params):
        client.calls.append((path, dict(params)))
        if path == "/recording/mbid-1":
            return 200, client._responses["mbid-1"]
        if path == "/work/work-1":
            return 200, {
                "relations": [
                    {
                        "target-type": "recording",
                        "recording": {"id": "mbid-1", "disambiguation": ""},
                    },
                    {
                        "target-type": "recording",
                        "recording": {"id": "mbid-studio", "disambiguation": ""},
                    },
                    {
                        "target-type": "recording",
                        "recording": {"id": "mbid-live", "disambiguation": "live, 2013-10-10"},
                    },
                ]
            }
        if path == "/recording/mbid-studio":
            return 200, {"releases": [{"date": "2012-10-05"}]}  # the true earliest release
        if path == "/recording/mbid-live":
            raise AssertionError("live-disambiguated recordings must not be fetched")
        raise AssertionError(f"unexpected path: {path}")

    client.get = get

    enrichment.enrich_song_metadata(tmp_conn, client)

    row = tmp_conn.execute("SELECT release_date FROM songs WHERE id = ?", (song_id,)).fetchone()
    assert row["release_date"] == "2012-10-05"


def test_enrich_song_metadata_without_a_linked_work_only_queries_the_recording(tmp_conn):
    song_id = _seed_resolved_song(tmp_conn, "Elephant", "mbid-1")
    client = FakeMbidClient(
        {"mbid-1": {"length": 275000, "releases": [{"date": "2012-10-05"}], "genres": [], "relations": []}}
    )

    enrichment.enrich_song_metadata(tmp_conn, client)

    row = tmp_conn.execute("SELECT release_date FROM songs WHERE id = ?", (song_id,)).fetchone()
    assert row["release_date"] == "2012-10-05"
    assert client.calls == [("/recording/mbid-1", enrichment.RECORDING_LOOKUP_PARAMS)]


def test_find_related_studio_recording_ids_excludes_live_and_self_and_respects_cap():
    work_payload = {
        "relations": [
            {"target-type": "recording", "recording": {"id": "self", "disambiguation": ""}},
            {"target-type": "recording", "recording": {"id": "live-1", "disambiguation": "live, 2013"}},
            {"target-type": "recording", "recording": {"id": "studio-1", "disambiguation": ""}},
            {"target-type": "recording", "recording": {"id": "studio-2", "disambiguation": "Remix"}},
            {"target-type": "recording", "recording": {"id": "studio-3", "disambiguation": ""}},
            {"target-type": "recording", "recording": {"id": "studio-4", "disambiguation": ""}},
            {"target-type": "recording", "recording": {"id": "studio-5", "disambiguation": ""}},
            {"target-type": "recording", "recording": {"id": "studio-6", "disambiguation": ""}},
            {"target-type": "work", "work": {"id": "not-a-recording"}},
        ]
    }

    result = enrichment._find_related_studio_recording_ids(work_payload, exclude_id="self")

    assert "self" not in result
    assert "live-1" not in result
    assert "not-a-recording" not in result
    assert len(result) == enrichment.MAX_RELATED_RECORDINGS


def test_enrich_song_metadata_skips_song_on_musicbrainz_error_and_continues(tmp_conn):
    _seed_resolved_song(tmp_conn, "Song A", "mbid-a")
    _seed_resolved_song(tmp_conn, "Song B", "mbid-b")

    class FlakyClient:
        def __init__(self):
            self.calls = 0

        def get(self, path, params):
            self.calls += 1
            if path == "/recording/mbid-a":
                raise MusicBrainzError("busy")
            return 200, {"length": 100, "releases": [], "genres": []}

    client = FlakyClient()

    enrichment.enrich_song_metadata(tmp_conn, client)  # must not raise

    assert client.calls == 2
