from datetime import datetime

from undercurrents.ingestion.models import (
    Artist,
    NormalizedSetlist,
    SetlistSongEntry,
    Tour,
    Venue,
)
from undercurrents.ingestion.raw_schema import RawSetlist


# Set names are typed by hand by setlist.fm contributors, so the same segment arrives as
# "B-Stage", "B Stage" and "B-stage". Only spelling is unified here, never meaning: "Stage A"
# and "Stage B" come from a venue that labels its stages that way and are left alone rather
# than being folded into the main/satellite pair, which would be a guess.
SET_NAME_CANONICAL = {
    "b stage": "B-Stage",
    "b-stage": "B-Stage",
    "b-stage - dj set": "B-Stage DJ Set",
    "main stage": "Main Stage",
    "stage a": "Stage A",
    "stage b": "Stage B",
    "acoustic": "Acoustic",
    "encore": "Encore",
}


def canonical_set_name(name: str | None) -> str | None:
    if not name or not name.strip():
        return None
    cleaned = " ".join(name.split())
    return SET_NAME_CANONICAL.get(cleaned.lower(), cleaned)


def normalize_setlist(raw: RawSetlist) -> NormalizedSetlist:
    event_date = datetime.strptime(raw.eventDate, "%d-%m-%Y").date().isoformat()

    artist = Artist(id=raw.artist.mbid, name=raw.artist.name, mbid=raw.artist.mbid)

    city = raw.venue.city
    coords = city.coords if city and city.coords else None
    # A coords object with no lat/long is the same as no coords at all.
    if coords is not None and (coords.lat is None or coords.long is None):
        coords = None

    venue = Venue(
        id=raw.venue.id,
        name=raw.venue.name,
        city=city.name if city else None,
        state=city.state if city else None,
        country=city.country.name if city else None,
        latitude=coords.lat if coords else None,
        longitude=coords.long if coords else None,
    )

    tour = Tour(name=raw.tour.name) if raw.tour else None

    songs: list[SetlistSongEntry] = []
    position = 0
    for set_number, raw_set in enumerate(raw.sets.set, start=1):
        is_encore = raw_set.encore is not None
        set_name = canonical_set_name(raw_set.name)
        for raw_song in raw_set.song:
            position += 1
            songs.append(
                SetlistSongEntry(
                    position=position,
                    set_number=set_number,
                    song_name=raw_song.name,
                    is_encore=is_encore,
                    is_cover=raw_song.cover is not None,
                    cover_artist_name=raw_song.cover.name if raw_song.cover else None,
                    is_tape=raw_song.tape,
                    info=raw_song.info,
                    set_name=set_name,
                    guest_name=raw_song.guest.name if raw_song.guest else None,
                    guest_mbid=raw_song.guest.mbid if raw_song.guest else None,
                )
            )

    info = raw.info.strip() if raw.info and raw.info.strip() else None

    return NormalizedSetlist(
        id=raw.id,
        event_date=event_date,
        last_updated_source=raw.lastUpdated,
        url=raw.url,
        artist=artist,
        venue=venue,
        tour=tour,
        songs=songs,
        info=info,
    )
