from pydantic import BaseModel, Field


class RawCountry(BaseModel):
    code: str
    name: str


class RawCoords(BaseModel):
    # Optional, because at least one show carries `"coords": {}`. Requiring them made the
    # whole setlist fail validation and lose its set names and guest credits along with it.
    lat: float | None = None
    long: float | None = None


class RawCity(BaseModel):
    name: str
    state: str | None = None
    country: RawCountry
    # setlist.fm ships city-level coordinates with every setlist. They were ignored for a
    # long time and geocoded again from Nominatim, which was wasted work: these cover 766 of
    # the 767 shows and cost nothing.
    coords: RawCoords | None = None


class RawVenue(BaseModel):
    id: str
    name: str
    city: RawCity | None = None


class RawArtist(BaseModel):
    mbid: str
    name: str


class RawTour(BaseModel):
    name: str


class RawCoverArtist(BaseModel):
    mbid: str | None = None
    name: str


class RawGuest(BaseModel):
    mbid: str | None = None
    name: str


class RawSong(BaseModel):
    name: str
    cover: RawCoverArtist | None = None
    info: str | None = None
    tape: bool = False
    # `with` is a Python keyword, so the field is aliased. It names a guest who performed
    # this song with the band.
    guest: RawGuest | None = Field(default=None, alias="with")


class RawSet(BaseModel):
    encore: int | None = None
    # Named segments: "B-Stage", "Acoustic", and occasionally an album title, which marks a
    # night the record was played in full.
    name: str | None = None
    song: list[RawSong] = Field(default_factory=list)


class RawSets(BaseModel):
    set: list[RawSet] = Field(default_factory=list)


class RawSetlist(BaseModel):
    id: str
    eventDate: str
    lastUpdated: str
    artist: RawArtist
    venue: RawVenue
    tour: RawTour | None = None
    sets: RawSets
    url: str
    info: str | None = None


class RawSetlistsPage(BaseModel):
    """Top-level page envelope. Individual `setlist` entries are kept as raw dicts
    and validated one by one in the pipeline, so that a single malformed entry
    doesn't invalidate an otherwise-good page."""

    type: str
    itemsPerPage: int
    page: int
    total: int
    setlist: list[dict] = Field(default_factory=list)


class RawArtistSearchResult(BaseModel):
    mbid: str
    name: str


class RawSearchArtistsResponse(BaseModel):
    type: str
    itemsPerPage: int
    page: int
    total: int
    artist: list[RawArtistSearchResult] = Field(default_factory=list)
