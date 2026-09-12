from datetime import date

from undercurrents.clustering import geography
from undercurrents.storage import db


def _setlist(conn, setlist_id, event_date, country):
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id=f"v-{setlist_id}", name="V", city="C", state=None, country=country)
    song = SetlistSongEntry(1, 1, "A", False, False, None, False, None)
    db.save_setlist(
        conn,
        NormalizedSetlist(
            id=setlist_id, event_date=event_date, last_updated_source="x",
            url=f"https://x/{setlist_id}", artist=artist, venue=venue, tour=None, songs=[song],
        ),
    )


def test_continent_for_country_known_countries():
    assert geography.continent_for_country("United States") == "North America"
    assert geography.continent_for_country("Australia") == "Oceania"
    assert geography.continent_for_country("Germany") == "Europe"
    assert geography.continent_for_country("Brazil") == "South America"
    assert geography.continent_for_country("Japan") == "Asia"


def test_continent_for_country_unknown_country_returns_none():
    assert geography.continent_for_country("Atlantis") is None


def test_country_show_count(tmp_conn):
    _setlist(tmp_conn, "s1", "2020-01-01", "Australia")
    _setlist(tmp_conn, "s2", "2020-02-01", "Australia")
    _setlist(tmp_conn, "s3", "2020-03-01", "United States")

    assert geography.country_show_count(tmp_conn, "Australia") == 2
    assert geography.country_show_count(tmp_conn, "United States") == 1
    assert geography.country_show_count(tmp_conn, "Atlantis") == 0


def test_days_since_country_last_visited(tmp_conn):
    _setlist(tmp_conn, "s1", "2020-01-01", "Australia")
    _setlist(tmp_conn, "s2", "2020-01-11", "Australia")

    result = geography.days_since_country_last_visited(tmp_conn, "Australia", date(2020, 2, 1))

    assert result == 21  # since 2020-01-11, the most recent prior visit


def test_days_since_country_last_visited_ignores_setlists_on_or_after_reference_date(tmp_conn):
    _setlist(tmp_conn, "s1", "2020-01-01", "Australia")
    _setlist(tmp_conn, "s2", "2020-06-01", "Australia")  # after the reference date

    result = geography.days_since_country_last_visited(tmp_conn, "Australia", date(2020, 2, 1))

    assert result == 31  # only s1 counts


def test_days_since_country_last_visited_none_when_never_visited(tmp_conn):
    _setlist(tmp_conn, "s1", "2020-01-01", "United States")

    assert geography.days_since_country_last_visited(tmp_conn, "Australia", date(2020, 2, 1)) is None


def test_days_since_continent_last_visited_aggregates_across_countries(tmp_conn):
    _setlist(tmp_conn, "s1", "2020-01-01", "Germany")
    _setlist(tmp_conn, "s2", "2020-01-11", "France")  # different country, same continent

    result = geography.days_since_continent_last_visited(tmp_conn, "Europe", date(2020, 2, 1))

    assert result == 21  # since France on 2020-01-11


def test_days_since_continent_last_visited_none_for_unknown_continent(tmp_conn):
    _setlist(tmp_conn, "s1", "2020-01-01", "Germany")

    assert geography.days_since_continent_last_visited(tmp_conn, "Nowhere", date(2020, 2, 1)) is None


def _setlist_at_venue(conn, setlist_id, event_date, venue_id):
    from undercurrents.ingestion.models import Artist, NormalizedSetlist, SetlistSongEntry, Venue

    artist = Artist(id="a1", name="Tame Impala", mbid="a1")
    venue = Venue(id=venue_id, name=venue_id, city="C", state=None, country="Country")
    song = SetlistSongEntry(1, 1, "A", False, False, None, False, None)
    db.save_setlist(
        conn,
        NormalizedSetlist(
            id=setlist_id, event_date=event_date, last_updated_source="x",
            url=f"https://x/{setlist_id}", artist=artist, venue=venue, tour=None, songs=[song],
        ),
    )


def test_venue_show_count(tmp_conn):
    _setlist_at_venue(tmp_conn, "s1", "2020-01-01", "venue-a")
    _setlist_at_venue(tmp_conn, "s2", "2020-02-01", "venue-a")
    _setlist_at_venue(tmp_conn, "s3", "2020-03-01", "venue-b")

    assert geography.venue_show_count(tmp_conn, "venue-a") == 2
    assert geography.venue_show_count(tmp_conn, "venue-b") == 1
    assert geography.venue_show_count(tmp_conn, "venue-c") == 0


def test_days_since_venue_last_visited(tmp_conn):
    _setlist_at_venue(tmp_conn, "s1", "2020-01-01", "venue-a")
    _setlist_at_venue(tmp_conn, "s2", "2020-01-11", "venue-a")

    result = geography.days_since_venue_last_visited(tmp_conn, "venue-a", date(2020, 2, 1))

    assert result == 21


def test_days_since_venue_last_visited_none_when_never_visited(tmp_conn):
    _setlist_at_venue(tmp_conn, "s1", "2020-01-01", "venue-a")

    assert geography.days_since_venue_last_visited(tmp_conn, "venue-b", date(2020, 2, 1)) is None
