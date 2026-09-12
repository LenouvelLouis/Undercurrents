from undercurrents.clustering import annotations
from undercurrents.storage import db


def test_classify_song_info_detects_debut():
    assert annotations.classify_song_info("Tour debut")["is_debut"] is True
    assert annotations.classify_song_info("Live debut, new mix")["is_debut"] is True
    assert annotations.classify_song_info("Just a regular play")["is_debut"] is False


def test_classify_song_info_detects_fan_request():
    flags = annotations.classify_song_info("Fan request, replaced Expectation")
    assert flags["is_fan_request"] is True


def test_classify_song_info_detects_tease():
    flags = annotations.classify_song_info("Preceded by Black Sabbath 'War Pigs' tease")
    assert flags["has_tease"] is True


def test_classify_song_info_detects_extended():
    assert annotations.classify_song_info("With extended jam outro")["was_extended"] is True
    assert annotations.classify_song_info("extended outro")["was_extended"] is True


def test_classify_song_info_detects_restarted():
    assert annotations.classify_song_info("restarted")["was_restarted"] is True
    assert annotations.classify_song_info("Restarted due to technical issue")["was_restarted"] is True


def test_classify_song_info_handles_none():
    flags = annotations.classify_song_info(None)
    assert all(value is False for value in flags.values())


def test_classify_song_info_flags_are_independent():
    flags = annotations.classify_song_info("Tour debut, fan request, with extended outro")
    assert flags["is_debut"] is True
    assert flags["is_fan_request"] is True
    assert flags["was_extended"] is True
    assert flags["has_tease"] is False
    assert flags["was_restarted"] is False


def test_classify_setlist_info_detects_incomplete():
    assert annotations.classify_setlist_info("Setlist incomplete")["is_incomplete"] is True


def test_classify_setlist_info_detects_out_of_order():
    flags = annotations.classify_setlist_info("incomplete and out of order")
    assert flags["is_incomplete"] is True
    assert flags["is_out_of_order"] is True


def test_classify_setlist_info_detects_disruption():
    assert annotations.classify_setlist_info("Show was cancelled due to lightning storm")["was_disrupted"] is True
    assert annotations.classify_setlist_info("Set cut short due to lightning storm")["was_disrupted"] is True
    assert annotations.classify_setlist_info("Set aborted due to problems with MIDI Keyboard")["was_disrupted"] is True


def test_classify_setlist_info_handles_none():
    flags = annotations.classify_setlist_info(None)
    assert all(value is False for value in flags.values())


def _setlist(conn, setlist_id, song_names, setlist_info=None, song_infos=None):
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id="v1", name="V", city="C", state=None, country="Country")
    song_infos = song_infos or [None] * len(song_names)
    songs = [
        SetlistSongEntry(i + 1, 1, name, False, False, None, False, song_infos[i])
        for i, name in enumerate(song_names)
    ]
    db.save_setlist(
        conn,
        NormalizedSetlist(
            id=setlist_id, event_date="2019-01-01", last_updated_source="x",
            url=f"https://x/{setlist_id}", artist=artist, venue=venue, tour=None,
            songs=songs, info=setlist_info,
        ),
    )


def test_annotated_song_plays_joins_flags_with_setlist_song_rows(tmp_conn):
    _setlist(tmp_conn, "s1", ["A", "B"], song_infos=["Tour debut", None])

    rows = annotations.annotated_song_plays(tmp_conn)

    by_position = {r["position"]: r for r in rows}
    assert by_position[1]["is_debut"] is True
    assert by_position[2]["is_debut"] is False


def test_annotated_setlists_joins_flags_with_setlists(tmp_conn):
    _setlist(tmp_conn, "s1", ["A"], setlist_info="Setlist incomplete")
    _setlist(tmp_conn, "s2", ["A"], setlist_info=None)

    rows = {r["setlist_id"]: r for r in annotations.annotated_setlists(tmp_conn)}

    assert rows["s1"]["is_incomplete"] is True
    assert rows["s2"]["is_incomplete"] is False


def test_flag_counts_aggregates_across_dataset(tmp_conn):
    _setlist(tmp_conn, "s1", ["A", "B"], song_infos=["Tour debut", "Fan request"])
    _setlist(tmp_conn, "s2", ["A"], setlist_info="Setlist incomplete")

    counts = annotations.flag_counts(tmp_conn)

    assert counts["song"]["is_debut"] == 1
    assert counts["song"]["is_fan_request"] == 1
    assert counts["setlist"]["is_incomplete"] == 1
