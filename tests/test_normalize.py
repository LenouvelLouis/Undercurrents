from undercurrents.ingestion.raw_schema import RawSetlist
from undercurrents.ingestion.normalize import normalize_setlist
from tests.helpers import make_raw_setlist_dict


def test_normalize_basic_setlist():
    raw = RawSetlist.model_validate(make_raw_setlist_dict())
    normalized = normalize_setlist(raw)

    assert normalized.id == "a1b2c3"
    assert normalized.event_date == "2019-08-30"
    assert normalized.tour.name == "Currents Tour"
    assert normalized.venue.city == "Perth"
    assert normalized.venue.country == "Australia"
    assert len(normalized.songs) == 1
    assert normalized.songs[0].song_name == "Let It Happen"
    assert normalized.songs[0].is_encore is False
    assert normalized.songs[0].is_cover is False
    assert normalized.songs[0].is_tape is False


def test_normalize_setlist_without_tour():
    raw = RawSetlist.model_validate(make_raw_setlist_dict(tour_name=None))
    normalized = normalize_setlist(raw)
    assert normalized.tour is None


def test_normalize_setlist_info_defaults_to_none():
    raw = RawSetlist.model_validate(make_raw_setlist_dict())
    normalized = normalize_setlist(raw)
    assert normalized.info is None


def test_normalize_setlist_info_is_captured():
    raw = RawSetlist.model_validate(make_raw_setlist_dict(info="Setlist incomplete"))
    normalized = normalize_setlist(raw)
    assert normalized.info == "Setlist incomplete"


def test_normalize_setlist_blank_info_becomes_none():
    raw = RawSetlist.model_validate(make_raw_setlist_dict(info="   "))
    normalized = normalize_setlist(raw)
    assert normalized.info is None


def test_normalize_cover_song():
    songs = [{"name": "Adventure of a Lifetime", "cover": {"name": "Coldplay"}}]
    raw = RawSetlist.model_validate(make_raw_setlist_dict(songs=songs))
    normalized = normalize_setlist(raw)

    entry = normalized.songs[0]
    assert entry.is_cover is True
    assert entry.cover_artist_name == "Coldplay"


def test_normalize_tape_song():
    songs = [{"name": "Intro", "tape": True}]
    raw = RawSetlist.model_validate(make_raw_setlist_dict(songs=songs))
    normalized = normalize_setlist(raw)
    assert normalized.songs[0].is_tape is True


def test_normalize_encore_and_multiple_sets():
    raw_dict = make_raw_setlist_dict()
    raw_dict["sets"] = {
        "set": [
            {"song": [{"name": "Let It Happen"}, {"name": "Elephant"}]},
            {"encore": 1, "song": [{"name": "New Person, Same Old Mistakes"}]},
        ]
    }
    raw = RawSetlist.model_validate(raw_dict)
    normalized = normalize_setlist(raw)

    assert [s.song_name for s in normalized.songs] == [
        "Let It Happen",
        "Elephant",
        "New Person, Same Old Mistakes",
    ]
    assert [s.set_number for s in normalized.songs] == [1, 1, 2]
    assert [s.position for s in normalized.songs] == [1, 2, 3]
    assert normalized.songs[0].is_encore is False
    assert normalized.songs[2].is_encore is True
