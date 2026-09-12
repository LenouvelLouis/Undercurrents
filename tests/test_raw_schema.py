import pytest
from pydantic import ValidationError

from undercurrents.ingestion.raw_schema import RawSetlist, RawSetlistsPage, RawSearchArtistsResponse
from tests.helpers import make_raw_setlist_dict


def test_raw_setlist_parses_full_fixture():
    parsed = RawSetlist.model_validate(make_raw_setlist_dict())
    assert parsed.id == "a1b2c3"
    assert parsed.artist.name == "Tame Impala"
    assert parsed.venue.city.country.code == "AU"
    assert parsed.tour.name == "Currents Tour"


def test_raw_setlist_allows_missing_tour():
    parsed = RawSetlist.model_validate(make_raw_setlist_dict(tour_name=None))
    assert parsed.tour is None


def test_raw_setlist_rejects_missing_required_field():
    data = make_raw_setlist_dict()
    del data["eventDate"]
    with pytest.raises(ValidationError):
        RawSetlist.model_validate(data)


def test_raw_setlists_page_keeps_setlist_entries_as_dicts():
    page = {
        "type": "setlists",
        "itemsPerPage": 20,
        "page": 1,
        "total": 1,
        "setlist": [make_raw_setlist_dict()],
    }
    parsed = RawSetlistsPage.model_validate(page)
    assert len(parsed.setlist) == 1
    assert parsed.setlist[0]["id"] == "a1b2c3"


def test_raw_search_artists_response_parses_candidates():
    payload = {
        "type": "artists",
        "itemsPerPage": 30,
        "page": 1,
        "total": 1,
        "artist": [{"mbid": "tame-impala-mbid-fake", "name": "Tame Impala"}],
    }
    parsed = RawSearchArtistsResponse.model_validate(payload)
    assert parsed.artist[0].name == "Tame Impala"
    assert parsed.artist[0].mbid == "tame-impala-mbid-fake"
