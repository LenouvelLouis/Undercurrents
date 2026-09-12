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
