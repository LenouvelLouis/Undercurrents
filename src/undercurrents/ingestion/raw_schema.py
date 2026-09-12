from pydantic import BaseModel, Field


class RawCountry(BaseModel):
    code: str
    name: str


class RawCity(BaseModel):
    name: str
    state: str | None = None
    country: RawCountry


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


class RawSong(BaseModel):
    name: str
    cover: RawCoverArtist | None = None
    info: str | None = None
    tape: bool = False


class RawSet(BaseModel):
    encore: int | None = None
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
