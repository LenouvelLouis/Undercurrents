def make_raw_setlist_dict(
    setlist_id="a1b2c3",
    event_date="30-08-2019",
    tour_name="Currents Tour",
    songs=None,
):
    if songs is None:
        songs = [{"name": "Let It Happen"}]
    return {
        "id": setlist_id,
        "eventDate": event_date,
        "lastUpdated": "2019-09-01T12:00:00.000+0000",
        "artist": {"mbid": "tame-impala-mbid-fake", "name": "Tame Impala"},
        "venue": {
            "id": "venue-1",
            "name": "Some Venue",
            "city": {
                "name": "Perth",
                "state": "WA",
                "country": {"code": "AU", "name": "Australia"},
            },
        },
        "tour": {"name": tour_name} if tour_name else None,
        "sets": {"set": [{"song": songs}]},
        "url": f"https://www.setlist.fm/setlist/tame-impala/{setlist_id}.html",
    }


def make_mbid_search_response(recordings=None):
    if recordings is None:
        recordings = [{"id": "fake-mbid-1", "score": 100, "title": "Elephant"}]
    return {
        "created": "2026-01-01T00:00:00.000Z",
        "count": len(recordings),
        "offset": 0,
        "recordings": recordings,
    }
