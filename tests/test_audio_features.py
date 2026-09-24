"""Audio-feature enrichment. No network: both clients are stubbed, which is the only way to
assert the thing that matters here, namely which recording gets asked about and in what order."""

import pytest

from undercurrents.clustering import audio_features
from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue
from undercurrents.storage import db


def _analysis(bpm=120.0, key="G", scale="minor", loudness=0.9, danceability=1.1):
    return {
        "0": {
            "rhythm": {"bpm": bpm, "danceability": danceability},
            "tonal": {"key_key": key, "key_scale": scale},
            "lowlevel": {"average_loudness": loudness},
        }
    }


class StubMusicBrainz:
    def __init__(self, recordings):
        self.recordings = recordings
        self.queries = []

    def get(self, path, params):
        self.queries.append(params["query"])
        return 200, {"recordings": [{"id": r} for r in self.recordings]}


class StubAcousticBrainz:
    def __init__(self, analysed):
        self.analysed = analysed
        self.asked = []

    def low_level(self, recording_ids):
        self.asked.append(list(recording_ids))
        return {r: self.analysed[r] for r in recording_ids if r in self.analysed}


def _save(conn, song_name, mbid=None, plays=1):
    db.ensure_songs_enrichment_columns(conn)
    for i in range(plays):
        db.save_setlist(
            conn,
            NormalizedSetlist(
                id=f"s{i}", event_date=f"2020-01-{i + 1:02d}", last_updated_source="x",
                url=f"https://x/{i}",
                artist=Artist(id="a1", name="Tame Impala", mbid="a1"),
                venue=Venue(id="v1", name="V", city="C", state=None, country="Country A"),
                tour=None,
                songs=[SetlistSongEntry(1, 1, song_name, False, False, None, False, None)],
            ),
        )
    if mbid:
        conn.execute("UPDATE songs SET mbid = ? WHERE name = ?", (mbid, song_name))
        conn.commit()


def test_the_stored_recording_is_tried_before_any_search(tmp_conn):
    _save(tmp_conn, "Elephant", mbid="stored-1")
    mb = StubMusicBrainz(["other-1"])
    ab = StubAcousticBrainz({"stored-1": _analysis(bpm=120.5)})

    audio_features.enrich(tmp_conn, mb_client=mb, ab_client=ab)

    assert ab.asked[0][0] == "stored-1", "the canonical recording has to be asked about first"
    row = tmp_conn.execute("SELECT bpm, audio_recording_mbid FROM songs").fetchone()
    assert row["bpm"] == 120.5
    assert row["audio_recording_mbid"] == "stored-1"


def test_a_song_is_recovered_from_another_recording_when_the_stored_one_is_not_analysed(tmp_conn):
    # This is the whole reason the module exists. Looking only at the stored mbid found 43 of
    # 81 songs and missed Elephant, Let It Happen and The Less I Know the Better, all three of
    # which are analysed under a different recording id.
    _save(tmp_conn, "Elephant", mbid="stored-1")
    mb = StubMusicBrainz(["alt-1", "alt-2"])
    ab = StubAcousticBrainz({"alt-2": _analysis(bpm=117.1, key="E", scale="major")})

    audio_features.enrich(tmp_conn, mb_client=mb, ab_client=ab)

    row = tmp_conn.execute("SELECT bpm, musical_key, audio_recording_mbid FROM songs").fetchone()
    assert row["bpm"] == 117.1
    assert row["musical_key"] == "E"
    assert row["audio_recording_mbid"] == "alt-2", (
        "the recording actually used must be stored: a tempo for one recording of Elephant "
        "is not the same claim as a tempo for Elephant"
    )


def test_a_song_nobody_analysed_is_left_unset(tmp_conn):
    _save(tmp_conn, "Deadbeat Jam", mbid="stored-1")
    result = audio_features.enrich(
        tmp_conn, mb_client=StubMusicBrainz(["alt-1"]), ab_client=StubAcousticBrainz({})
    )

    assert result["resolved"] == 0 and result["unresolved"] == 1
    assert tmp_conn.execute("SELECT bpm FROM songs").fetchone()["bpm"] is None


def test_a_song_already_enriched_is_not_looked_up_again(tmp_conn):
    _save(tmp_conn, "Elephant", mbid="stored-1")
    ab = StubAcousticBrainz({"stored-1": _analysis()})
    audio_features.enrich(tmp_conn, mb_client=StubMusicBrainz([]), ab_client=ab)
    calls = len(ab.asked)

    audio_features.enrich(tmp_conn, mb_client=StubMusicBrainz([]), ab_client=ab)
    assert len(ab.asked) == calls, "a second run must not re-query what it already resolved"


def test_an_analysis_without_a_tempo_is_rejected(tmp_conn):
    # A document can exist and still be useless. Treating it as a hit would write NULLs over
    # a song that another recording could have answered.
    _save(tmp_conn, "Elephant", mbid="stored-1")
    empty = {"0": {"rhythm": {}, "tonal": {}, "lowlevel": {}}}
    result = audio_features.enrich(
        tmp_conn,
        mb_client=StubMusicBrainz([]),
        ab_client=StubAcousticBrainz({"stored-1": empty}),
    )
    assert result["resolved"] == 0


def test_extract_handles_a_document_without_the_submission_wrapper():
    direct = _analysis()["0"]
    assert audio_features._extract(direct)["bpm"] == 120.0
    assert audio_features._extract({}) is None
    assert audio_features._extract(None) is None


def test_coverage_reports_songs_and_performances_separately(tmp_conn):
    # They differ on purpose: the analysed songs skew towards the ones played most, so the
    # performance figure is far higher than the catalogue figure and both belong on the page.
    _save(tmp_conn, "Played a lot", mbid="m1", plays=5)
    _save(tmp_conn, "Played once", mbid="m2", plays=1)
    audio_features.ensure_columns(tmp_conn)
    tmp_conn.execute("UPDATE songs SET bpm = 120 WHERE name = 'Played a lot'")
    tmp_conn.commit()

    stats = audio_features.coverage(tmp_conn)
    assert stats["songs_with_audio"] == 1 and stats["songs_total"] == 2
    assert stats["song_coverage"] == 0.5
    assert stats["performance_coverage"] > stats["song_coverage"]


def test_the_search_asks_for_the_right_title_and_artist(tmp_conn):
    _save(tmp_conn, "Let It Happen")
    mb = StubMusicBrainz([])
    audio_features.enrich(tmp_conn, mb_client=mb, ab_client=StubAcousticBrainz({}))
    assert 'recording:"Let It Happen"' in mb.queries[0]
    assert 'artist:"Tame Impala"' in mb.queries[0]
