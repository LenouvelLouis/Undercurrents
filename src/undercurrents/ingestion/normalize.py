from datetime import datetime

from undercurrents.ingestion.models import (
    Artist,
    NormalizedSetlist,
    SetlistSongEntry,
    Tour,
    Venue,
)
from undercurrents.ingestion.raw_schema import RawSetlist


def normalize_setlist(raw: RawSetlist) -> NormalizedSetlist:
    event_date = datetime.strptime(raw.eventDate, "%d-%m-%Y").date().isoformat()

    artist = Artist(id=raw.artist.mbid, name=raw.artist.name, mbid=raw.artist.mbid)

    city = raw.venue.city
    venue = Venue(
        id=raw.venue.id,
        name=raw.venue.name,
        city=city.name if city else None,
        state=city.state if city else None,
        country=city.country.name if city else None,
    )

    tour = Tour(name=raw.tour.name) if raw.tour else None

    songs: list[SetlistSongEntry] = []
    position = 0
    for set_number, raw_set in enumerate(raw.sets.set, start=1):
        is_encore = raw_set.encore is not None
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
                )
            )

    return NormalizedSetlist(
        id=raw.id,
        event_date=event_date,
        last_updated_source=raw.lastUpdated,
        url=raw.url,
        artist=artist,
        venue=venue,
        tour=tour,
        songs=songs,
    )
