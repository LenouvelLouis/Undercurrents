from dataclasses import dataclass, field


@dataclass(frozen=True)
class Artist:
    id: str
    name: str
    mbid: str | None


@dataclass(frozen=True)
class Venue:
    id: str
    name: str
    city: str | None
    state: str | None
    country: str | None
    # City-level, straight from the setlist.fm payload. None only where the payload omits it.
    latitude: float | None = None
    longitude: float | None = None


@dataclass(frozen=True)
class Tour:
    name: str


@dataclass(frozen=True)
class SetlistSongEntry:
    position: int
    set_number: int
    song_name: str
    is_encore: bool
    is_cover: bool
    cover_artist_name: str | None
    is_tape: bool
    info: str | None
    # The name of the segment this song sat in: "B-Stage", "Acoustic", or an album title on
    # a night the record was played in full. Most sets are unnamed.
    set_name: str | None = None
    # Someone who performed this song with the band, when the source names one.
    guest_name: str | None = None
    guest_mbid: str | None = None


@dataclass(frozen=True)
class NormalizedSetlist:
    id: str
    event_date: str
    last_updated_source: str
    url: str
    artist: Artist
    venue: Venue
    tour: Tour | None
    songs: list[SetlistSongEntry] = field(default_factory=list)
    info: str | None = None
