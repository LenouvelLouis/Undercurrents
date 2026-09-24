from undercurrents.clustering import albums


def _release(title, primary, date, tracks, secondary=None, rid="rg"):
    return {
        "title": title,
        "date": date,
        "release-group": {"id": f"{rid}-{title}", "title": title, "primary-type": primary, "secondary-types": secondary or [], "first-release-date": date},
        "media": [{"tracks": [{"title": t, "recording": {"id": f"rec-{t}", "title": t}} for t in tracks]}],
    }


def test_normalize_title_ignores_apostrophe_style_case_and_brackets():
    assert albums.normalize_title("Why Won’t You Make Up Your Mind?") == albums.normalize_title("why won't you make up your mind")
    assert albums.normalize_title("Let It Happen (Edit)") == "let it happen"
    assert albums.normalize_title("Rock & Roll") == "rock and roll"


def test_album_beats_single_and_live_releases_are_ignored():
    releases = [
        _release("Let It Happen", "Single", "2015-03-01", ["Let It Happen"]),
        _release("Currents", "Album", "2015-07-15", ["Let It Happen", "Eventually"]),
        _release("Live Versions", "Album", "2014-01-01", ["Elephant"], secondary=["Live"]),
    ]
    by_title, by_recording = albums.build_index(releases)
    assert by_title["let it happen"]["album"] == "Currents"
    assert "elephant" not in by_title
    assert by_recording["rec-Eventually"]["album_type"] == "Album"


def test_an_ep_song_stays_on_the_ep_and_reissue_bonus_tracks_are_ignored():
    releases = [
        _release("Tame Impala", "EP", "2008-10-10", ["Half Full Glass of Wine"]),
        _release("Innerspeaker", "Album", "2010-05-21", ["Alter Ego", "Half Full Glass of Wine"]),
        # a later edition of the same record, with a bonus track from another era
        {**_release("Innerspeaker", "Album", "2020-05-21", ["Alter Ego", "Let It Happen"]),
         "release-group": {"id": "rg-Innerspeaker", "title": "Innerspeaker", "primary-type": "Album", "secondary-types": [], "first-release-date": "2010-05-21"}},
        _release("Currents", "Album", "2015-07-15", ["Let It Happen"]),
    ]
    by_title, _ = albums.build_index(releases)
    assert by_title["half full glass of wine"]["album"] == "Tame Impala"
    assert by_title["let it happen"]["album"] == "Currents"


def test_a_song_only_on_a_reissue_is_kept_as_a_bonus_track():
    releases = [
        _release("Lonerism", "Album", "2012-10-05", ["Elephant"]),
        {**_release("Lonerism", "Album", "2022-10-05", ["Elephant", "Island Walking"]),
         "release-group": {"id": "rg-Lonerism", "title": "Lonerism", "primary-type": "Album", "secondary-types": [], "first-release-date": "2012-10-05"}},
    ]
    by_title, _ = albums.build_index(releases)
    assert by_title["elephant"]["album_type"] == "Album"
    assert by_title["island walking"] == {"album": "Lonerism", "album_type": "Bonus", "album_date": "2012-10-05", "album_mbid": "rg-Lonerism"}


def test_assign_albums_matches_by_mbid_then_title_and_fills_missing_dates(tmp_conn):
    from undercurrents.storage import db

    db.ensure_songs_clustering_columns(tmp_conn)
    db.ensure_songs_enrichment_columns(tmp_conn)
    tmp_conn.execute("INSERT INTO songs (id, name, mbid) VALUES (1, 'Whatever Title', 'rec-Eventually')")
    tmp_conn.execute("INSERT INTO songs (id, name) VALUES (2, 'Let it happen')")
    tmp_conn.execute("INSERT INTO songs (id, name) VALUES (3, 'A Cover Song')")
    releases = [_release("Currents", "Album", "2015-07-15", ["Let It Happen", "Eventually"])]

    summary = albums.assign_albums(tmp_conn, releases=releases)

    assert summary == {"releases_scanned": 1, "matched_by_mbid": 1, "matched_by_title": 1, "unmatched": 1, "release_dates_filled": 2}
    rows = {r["id"]: r for r in tmp_conn.execute("SELECT id, album, release_date FROM songs")}
    assert rows[1]["album"] == "Currents" and rows[2]["album"] == "Currents"
    assert rows[3]["album"] is None
    assert rows[2]["release_date"] == "2015-07-15"
