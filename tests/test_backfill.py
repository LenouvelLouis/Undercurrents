"""Reading back the fields the normalizer used to skip, straight from stored payloads."""

import json

from undercurrents.ingestion import backfill
from undercurrents.ingestion.normalize import canonical_set_name, normalize_setlist
from undercurrents.ingestion.raw_schema import RawSetlist
from undercurrents.storage import db


def _raw(setlist_id="s1", coords={"lat": 48.85, "long": 2.35}, set_name="B-Stage", guest=None):
    song = {"name": "A"}
    if guest:
        song["with"] = guest
    return {
        "id": setlist_id,
        "eventDate": "01-01-2020",
        "lastUpdated": "2020-01-02T00:00:00.000+0000",
        "url": f"https://x/{setlist_id}",
        "artist": {"mbid": "a1", "name": "Tame Impala"},
        "venue": {
            "id": "v1",
            "name": "Venue",
            "city": {"name": "Paris", "country": {"code": "FR", "name": "France"}, **({"coords": coords} if coords is not None else {})},
        },
        "sets": {"set": [{"name": set_name, "song": [song]}]},
    }


def _store(conn, payload, endpoint="/artist/x/setlists"):
    conn.execute(
        "INSERT INTO raw_responses (endpoint, params_hash, fetched_at, http_status, payload_json)"
        " VALUES (?, ?, ?, ?, ?)",
        (endpoint, endpoint + str(id(payload)), "2020-01-01", 200, json.dumps({"setlist": [payload]})),
    )
    conn.commit()


def _prepare(conn, payload):
    db.ensure_venues_coordinate_columns(conn)
    db.ensure_setlist_songs_context_columns(conn)
    db.save_setlist(conn, normalize_setlist(RawSetlist.model_validate(payload)))
    conn.execute("UPDATE venues SET latitude = NULL, longitude = NULL")
    conn.execute("UPDATE setlist_songs SET set_name = NULL, guest_name = NULL, guest_mbid = NULL")
    conn.commit()


# --------------------------------------------------------------------------- normalizing


def test_coordinates_come_off_the_payload():
    normalized = normalize_setlist(RawSetlist.model_validate(_raw()))
    assert normalized.venue.latitude == 48.85
    assert normalized.venue.longitude == 2.35


def test_an_empty_coords_object_is_the_same_as_none():
    # One show really does ship "coords": {}. Requiring lat/long there made the whole setlist
    # fail validation and lose its set names and guest credits with it.
    normalized = normalize_setlist(RawSetlist.model_validate(_raw(coords={})))
    assert normalized.venue.latitude is None
    assert normalized.venue.longitude is None
    assert normalized.songs, "the rest of the setlist must survive a missing coordinate"


def test_a_guest_is_read_from_the_with_field():
    normalized = normalize_setlist(
        RawSetlist.model_validate(_raw(guest={"mbid": "g1", "name": "Dua Lipa"}))
    )
    assert normalized.songs[0].guest_name == "Dua Lipa"
    assert normalized.songs[0].guest_mbid == "g1"


def test_set_name_spelling_is_unified_but_meaning_is_not():
    assert canonical_set_name("B Stage") == "B-Stage"
    assert canonical_set_name("B-stage") == "B-Stage"
    assert canonical_set_name("Main stage") == "Main Stage"
    # Stage A and Stage B come from a venue that labels its stages that way; folding them
    # into the main/satellite pair would be a guess, so they are left alone.
    assert canonical_set_name("Stage A") == "Stage A"
    assert canonical_set_name("Stage B") == "Stage B"
    # An unknown name keeps its own spelling rather than being dropped.
    assert canonical_set_name("Acoustic Encore") == "Acoustic Encore"
    assert canonical_set_name("   ") is None
    assert canonical_set_name(None) is None


# --------------------------------------------------------------------------- backfilling


def test_backfill_fills_coordinates_set_names_and_guests(tmp_conn):
    payload = _raw(guest={"mbid": "g1", "name": "Dua Lipa"})
    _prepare(tmp_conn, payload)
    _store(tmp_conn, payload)

    result = backfill.backfill(tmp_conn)

    assert result["venues_given_coordinates"] == 1
    assert result["set_names_written"] == 1
    assert result["guest_credits_written"] == 1
    venue = tmp_conn.execute("SELECT latitude, longitude FROM venues").fetchone()
    assert (venue["latitude"], venue["longitude"]) == (48.85, 2.35)
    song = tmp_conn.execute("SELECT set_name, guest_name FROM setlist_songs").fetchone()
    assert (song["set_name"], song["guest_name"]) == ("B-Stage", "Dua Lipa")


def test_backfill_never_overwrites_a_coordinate_it_did_not_supply(tmp_conn):
    # A venue may have been geocoded for a payload that carries no coordinates. Replacing
    # that with the payload's value, or with NULL, would be a regression.
    payload = _raw()
    _prepare(tmp_conn, payload)
    _store(tmp_conn, payload)
    tmp_conn.execute("UPDATE venues SET latitude = 1.0, longitude = 2.0")
    tmp_conn.commit()

    backfill.backfill(tmp_conn)

    venue = tmp_conn.execute("SELECT latitude, longitude FROM venues").fetchone()
    assert (venue["latitude"], venue["longitude"]) == (1.0, 2.0)


def test_set_names_are_only_rewritten_when_asked(tmp_conn):
    payload = _raw()
    _prepare(tmp_conn, payload)
    _store(tmp_conn, payload)
    tmp_conn.execute("UPDATE setlist_songs SET set_name = 'Hand edited'")
    tmp_conn.commit()

    backfill.backfill(tmp_conn)
    assert tmp_conn.execute("SELECT set_name FROM setlist_songs").fetchone()[0] == "Hand edited"

    # overwrite exists for the case that matters: the spelling map changed and stored values
    # need bringing back in line with it.
    backfill.backfill(tmp_conn, overwrite_song_context=True)
    assert tmp_conn.execute("SELECT set_name FROM setlist_songs").fetchone()[0] == "B-Stage"


def test_a_malformed_payload_entry_does_not_stop_the_others(tmp_conn):
    good = _raw("s1")
    _prepare(tmp_conn, good)
    _store(tmp_conn, good)
    tmp_conn.execute(
        "INSERT INTO raw_responses (endpoint, params_hash, fetched_at, http_status, payload_json)"
        " VALUES (?, ?, ?, ?, ?)",
        ("/broken", "broken", "2020-01-01", 200, json.dumps({"setlist": [{"id": "s9"}]})),
    )
    tmp_conn.commit()

    result = backfill.backfill(tmp_conn)
    assert result["setlists_skipped"] == 1
    assert result["venues_given_coordinates"] == 1, "the good entry still had to land"


def test_the_freshest_copy_of_a_setlist_wins(tmp_conn):
    # Pages overlap and re-fetches produce newer copies of the same setlist.
    old = _raw("s1", set_name="Main Stage")
    _prepare(tmp_conn, old)
    _store(tmp_conn, old, endpoint="/page1")
    _store(tmp_conn, _raw("s1", set_name="Acoustic"), endpoint="/page2")

    backfill.backfill(tmp_conn, overwrite_song_context=True)
    assert tmp_conn.execute("SELECT set_name FROM setlist_songs").fetchone()[0] == "Acoustic"
