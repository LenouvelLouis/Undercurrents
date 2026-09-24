"""The note classifier, and the check that keeps its debut flag honest."""

from undercurrents.derived import notes
from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue
from undercurrents.storage import db


def _entry(position, name, info=None):
    return SetlistSongEntry(position, 1, name, False, False, None, False, info)


def _save(conn, setlist_id, event_date, songs):
    db.save_setlist(
        conn,
        NormalizedSetlist(
            id=setlist_id, event_date=event_date, last_updated_source="x",
            url=f"https://x/{setlist_id}",
            artist=Artist(id="a1", name="Tame Impala", mbid="a1"),
            venue=Venue(id="v1", name="Venue", city="City", state=None, country="Country A"),
            tour=None, songs=songs,
        ),
    )


def test_a_plain_debut_is_flagged():
    assert notes.classify("Live debut")["flags"]["debut"] is True
    assert notes.classify("live debut")["flags"]["debut"] is True


def test_a_return_after_years_is_not_a_debut():
    # "First time played" and "First time played since 2015" mean opposite things. An earlier
    # version of the pattern scored 17 returns as debuts, which the archive check caught.
    for text in [
        "First time played since August 7th 2015, extended outro",
        "First time played live since 2010",
        "first performance since 29 October 2011",
        "First time played during this EU tour",
        "first performance of the album version",
    ]:
        flags = notes.classify(text)["flags"]
        assert flags["debut"] is False, text
    assert notes.classify("First time played since 2015")["flags"]["long_awaited_return"] is True


def test_every_flag_records_the_phrase_that_set_it():
    result = notes.classify("Instrumental; dedicated to Julien")
    assert result["flags"]["instrumental"] and result["flags"]["dedication"]
    assert result["evidence"]["instrumental"].lower() == "instrumental"
    assert "dedicat" in result["evidence"]["dedication"].lower()


def test_a_note_with_nothing_recognisable_sets_no_flags():
    result = notes.classify("feel like this was on earlier in set")
    assert not any(result["flags"].values())
    assert result["evidence"] == {}


def test_an_empty_note_is_handled():
    for value in (None, "", "   "):
        assert not any(notes.classify(value)["flags"].values())
        assert notes.extract_teases(value) == []


# ------------------------------------------------------------------- tease extraction


def test_quoted_titles_are_extracted_in_order():
    assert notes.extract_teases('w/ "Mind Melt" + "Jazz Prog Odyssey 3070" outro') == [
        "Mind Melt",
        "Jazz Prog Odyssey 3070",
    ]


def test_an_apostrophe_inside_a_title_does_not_truncate_it():
    # A single class of openers and another of closers let a double quote open and an
    # apostrophe close, which turned this title into "Why Won".
    assert notes.extract_teases('"Why Won\'t They Talk To Me?" was requested') == [
        "Why Won't They Talk To Me?"
    ]


def test_placeholder_jam_names_are_not_treated_as_titles():
    assert notes.extract_teases("'New' Jam") == []
    assert notes.extract_teases("'Newer' Jam") == []


def test_curly_quotes_are_understood():
    assert notes.extract_teases("Preceded by “Half Full Glass of Wine” tease") == [
        "Half Full Glass of Wine"
    ]


def test_a_title_is_not_repeated():
    assert notes.extract_teases("'Sestri Levante' outro, then 'Sestri Levante' again") == [
        "Sestri Levante"
    ]


# ------------------------------------------------------------------- rebuild and verify


def test_rebuild_only_stores_songs_that_carry_a_note(tmp_conn):
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "A", "Live debut"), _entry(2, "B")])
    result = notes.rebuild(tmp_conn)

    assert result["notes_classified"] == 1
    rows = tmp_conn.execute("SELECT song_id, is_debut FROM performance_notes").fetchall()
    assert len(rows) == 1 and rows[0]["is_debut"] == 1


def test_rebuild_is_idempotent(tmp_conn):
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "A", "Reprise")])
    first = notes.rebuild(tmp_conn)
    second = notes.rebuild(tmp_conn)
    assert first["by_flag"] == second["by_flag"]
    assert tmp_conn.execute("SELECT COUNT(*) FROM performance_notes").fetchone()[0] == 1


def test_a_debut_claim_on_the_earliest_show_is_confirmed(tmp_conn):
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "A", "Live debut")])
    _save(tmp_conn, "s2", "2020-02-01", [_entry(1, "A")])
    notes.rebuild(tmp_conn)

    verdict = notes.verify_debuts(tmp_conn)
    assert verdict["claims"] == 1 and verdict["confirmed"] == 1 and verdict["contradicted"] == 0


def test_a_debut_claim_with_an_earlier_performance_is_contradicted(tmp_conn):
    # The note says debut, the archive says it was played eleven months earlier. The check
    # reports the discrepancy rather than trusting either side.
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "A")])
    _save(tmp_conn, "s2", "2020-12-01", [_entry(1, "A", "Live debut")])
    notes.rebuild(tmp_conn)

    verdict = notes.verify_debuts(tmp_conn)
    assert verdict["contradicted"] == 1
    contradiction = verdict["contradictions"][0]
    assert contradiction["claimed_on"] == "2020-12-01"
    assert contradiction["earliest_in_archive"] == "2020-01-01"
    assert contradiction["days_earlier"] == 335


def test_a_new_flag_is_added_to_an_existing_table(tmp_conn, monkeypatch):
    # CREATE TABLE IF NOT EXISTS does nothing to a table that already exists, so a flag added
    # to PATTERNS has to arrive by migration or every insert fails.
    _save(tmp_conn, "s1", "2020-01-01", [_entry(1, "A", "Reprise")])
    notes.rebuild(tmp_conn)

    monkeypatch.setattr(notes, "PATTERNS", {**notes.PATTERNS, "moon_phase": r"(?i)\bmoon\b"})
    monkeypatch.setattr(notes, "FLAGS", tuple(notes.PATTERNS))
    notes.rebuild(tmp_conn)

    columns = {r["name"] for r in tmp_conn.execute("PRAGMA table_info(performance_notes)")}
    assert "is_moon_phase" in columns
