CREATE TABLE IF NOT EXISTS raw_responses (
    id            INTEGER PRIMARY KEY,
    endpoint      TEXT NOT NULL,
    params_hash   TEXT NOT NULL,
    fetched_at    TEXT NOT NULL,
    http_status   INTEGER NOT NULL,
    payload_json  TEXT NOT NULL,
    UNIQUE(endpoint, params_hash)
);

CREATE TABLE IF NOT EXISTS artists (
    id    TEXT PRIMARY KEY,
    name  TEXT NOT NULL,
    mbid  TEXT
);

CREATE TABLE IF NOT EXISTS tours (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    year_start  INTEGER NOT NULL,
    year_end    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS venues (
    id       TEXT PRIMARY KEY,
    name     TEXT NOT NULL,
    city     TEXT,
    state    TEXT,
    country  TEXT
);

CREATE TABLE IF NOT EXISTS setlists (
    id                  TEXT PRIMARY KEY,
    event_date          TEXT NOT NULL,
    tour_id             INTEGER REFERENCES tours(id),
    venue_id            TEXT REFERENCES venues(id),
    artist_id           TEXT REFERENCES artists(id),
    url                 TEXT NOT NULL,
    last_updated_source TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS songs (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS setlist_songs (
    setlist_id       TEXT NOT NULL REFERENCES setlists(id),
    position         INTEGER NOT NULL,
    set_number       INTEGER NOT NULL,
    song_id          INTEGER NOT NULL REFERENCES songs(id),
    is_encore        INTEGER NOT NULL DEFAULT 0,
    is_cover         INTEGER NOT NULL DEFAULT 0,
    cover_artist_id  TEXT REFERENCES artists(id),
    is_tape          INTEGER NOT NULL DEFAULT 0,
    info             TEXT,
    PRIMARY KEY (setlist_id, position)
);
