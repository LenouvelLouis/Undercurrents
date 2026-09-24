# Undercurrents

A data analysis and prediction system exploring 18 years of Tame Impala setlists. This project ingests structural data from setlist.fm and MusicBrainz (approximately 750 setlists spanning 2008 to 2026), cleans and disambiguates song titles, applies clustering for pattern discovery, enriches songs/venues with additional structural metadata, and predicts song appearances in upcoming performances, all presented through a psychedelic and retro-futuristic web UI with a dedicated view per capability.

**Status:** Phases 0-2 (ingestion, clustering, prediction) implemented, plus a round of feature enrichment on top (positional prediction features, MusicBrainz metadata, geographic touring cadence, venue capacity). A natural-language chat agent (Phase 3) was built and validated, then removed to keep the focus on classical data analysis/prediction — see the project's internal notes for the full history and roadmap.

## Setup

### Prerequisites

- Python 3.12+
- `uv` (fast Python package installer)

### Installation

1. Clone the repository and install dependencies:

```bash
uv sync
```

2. Copy the example environment file and fill in your API key:

```bash
cp .env.example .env
```

3. In the `.env` file, add your setlist.fm API key (see next section for how to obtain one).

## Getting a setlist.fm API key

To fetch setlist data, you'll need a free API key from setlist.fm:

1. Create a free account at [setlist.fm](https://www.setlist.fm/)
2. Visit your account settings and request an API key using the form provided
3. Describe your use case (e.g., "Personal music analysis project" or "Non-commercial hobby research")
4. A basic key for personal, non-commercial use is typically issued right away

For API details and rate limits, see the official documentation: https://api.setlist.fm/docs/1.0/index.html

## Running the ingestion pipeline

The ingestion pipeline fetches all available Tame Impala setlists from setlist.fm, normalizes the data, and stores it in a local SQLite database:

```bash
uv run python -m undercurrents.ingestion.cli fetch
```

This command:
- Fetches every available Tame Impala setlist from the API
- Normalizes and structures the data (songs, dates, venues, tour names, set order)
- Stores the result in `data/undercurrents.db` (SQLite, gitignored)
- Caches API responses, so re-running is safe and inexpensive (already-fetched pages are skipped)

Optional flags:
- `--force-refresh`: Bypass the cache and refetch all data from the API
- `--db-path <path>`: Specify a custom path for the database file (default: `data/undercurrents.db`)

## Running the clustering pipeline

Once `data/undercurrents.db` has been populated by the ingestion pipeline, resolve song
titles, enrich metadata, and compute the setlist/song clustering:

```bash
uv run python -m undercurrents.clustering.cli run
```

This:
- Desambiguates song titles (MusicBrainz + a manual alias table for spelling variants and non-song entries like intros/jams)
- Enriches resolved songs with release date, duration, and genre tags from MusicBrainz
- Looks up venue capacity on Wikidata where an unambiguous match exists (conservative — many venues won't match, by design; see `CLAUDE.md` for a known networking caveat with this step)
- Clusters setlists and songs into a 2D embedding stored in `data/undercurrents.db` (`setlist_clusters`, `song_clusters` tables)

Add `--force-refresh` to re-resolve/re-enrich everything and recompute every cluster from scratch, and `--db-path` to use a different database file.

## Running the prediction agent

Once `data/undercurrents.db` has clustering data, rank songs by likelihood of
appearing in an upcoming show:

```bash
uv run python -m undercurrents.prediction.cli predict
```

Add `--date YYYY-MM-DD` to predict as of a specific date instead of today, and `--db-path` to
use a different database file. To measure how well the model actually predicts real shows it
hasn't seen:

```bash
uv run python -m undercurrents.prediction.cli evaluate
```

This holds out the most recent real shows (`--holdout-shows`, default 10), trains on
everything before them, and reports the mean top-N accuracy: for each held-out show, what
fraction of the songs actually played were among the model's N highest-probability
predictions (N = the number of songs actually played that night). `PredictionAgent` also
exposes `predict_opener_probability`, `predict_closer_probability`, and
`predict_encore_probability` per song.

## Running the web app

Once `data/undercurrents.db` has clustering and prediction data (Phases 0-2), the web frontend
reads it through a read-only FastAPI layer. Start both servers, each in its own terminal:

```bash
uv run uvicorn undercurrents.api.app:app --reload --port 8000
cd web && npm run dev
```

Open the printed Vite URL (usually `http://localhost:5173`) — the dev server proxies `/api/*`
requests to the FastAPI backend on port 8000. The app opens on a landing page with headline
stats, then two tabs (Predictions, Data Analysis) with five screens each, all backed by real
data from `data/undercurrents.db`.

The prediction endpoints serve from frozen models cached in `data/models/` (falling back to
training on first use if that directory is empty). After ingesting new data, refresh the
frozen models before restarting the API so predictions reflect it:

```bash
uv run python -m undercurrents.prediction.cli train-models
```

## Derived feature tables

Two tables of per-song and per-show features, recomputed from the ingested rows:

```bash
uv run python -m undercurrents.derived.cli build
```

`song_features` records, for every song, how often it was played, when it was first and last
heard, its longest absence, its current run of consecutive shows, and how often it opens or
closes a set. `setlist_features` records, for every show, the song count, encores, covers,
the opener and closer, the summed duration where every song's length is known, how much of
the set was new compared with the previous night, and the distance travelled since it. Both
are pure recomputations, so the command is safe to re-run at any time.

## Venue enrichment

Capacity, in batches, through Wikidata's SPARQL endpoint (the interface they document for
bulk reads; the per-venue search API answers a full run with a 403 and is right to):

```bash
uv run python -c "from pathlib import Path; from undercurrents.clustering import venue_capacity_bulk; from undercurrents.storage import db; conn = db.get_connection(Path('data/undercurrents.db')); db.initialize_schema(conn); print(venue_capacity_bulk.enrich(conn))"
```

A name is accepted only when it resolves to exactly one capacity within the venue's own
country, checked against both the Wikidata label and its aliases, so ambiguous names are
left unset rather than guessed at.

Coordinates, via Nominatim, one lookup per distinct city rather than per venue, serial and
rate-limited to respect their usage policy:

```bash
uv run python -c "from pathlib import Path; from undercurrents.clustering import geocode; from undercurrents.storage import db; conn = db.get_connection(Path('data/undercurrents.db')); db.initialize_schema(conn); print(geocode.enrich(conn))"
```

Coordinates are city-level, which is what the distance figures need; run
`undercurrents.derived.cli build` afterwards so the travel columns pick them up.

## Model benchmarks

Trains every experimental model, scores it against the simplest baseline that could do the
same job, and writes the comparison to `data/models/benchmarks.json`:

```bash
uv run python -m undercurrents.benchmarks.cli run
```

The split is strictly chronological (the most recent shows are held out, never a random
sample). Three experiments run: a GRU against a first-order Markov chain on next-song
prediction, an MLP against the production logistic regression on song-appearance prediction,
and item2vec embeddings learned from setlist co-occurrence. The web app reads the stored file
at `/api/predictions/benchmarks` and shows each model beside its baseline, including the
cases where the baseline wins.

## The three sequence and rotation predictions

Three predictions live outside the original five and are served from
`/api/predictions/running-order`, `/api/predictions/encore` and `/api/predictions/comeback`.
All three are trained and backtested by the same command as the rest:

```bash
uv run python -m undercurrents.prediction.cli train-models --with-sequence
```

The flag is what separates the two speeds. Without it the command fits the five sklearn
models in under a second, as before. With it, it also fits the GRU used for the running order
and replays every held-out show for the three backtests, which takes a few minutes, and
writes `running_order.joblib` plus one JSON of results per prediction into `data/models/`.
Nothing here is ever trained inside a request. A backtest that cannot run for want of history
is reported as skipped rather than failing the command.

**Running order** (`prediction/running_order.py`) writes the set out first song to last
rather than ranking the catalogue. It reuses the GRU from the benchmark module and decodes
greedily, masking songs already played that night. The backtest sweeps the length of the seed
it is given, because the model is weak inventing a whole night from nothing (0.32 of the set,
worse than a static most-played list at 0.45) and much stronger continuing one that has
already started (0.89 given a single real opening song). Reporting only one end of that range
would misdescribe the page, so the sweep also carries a `production` run scored exactly the
way the page runs: seeded with the *previous* show's opening, with those seeded songs counted
as guesses rather than given for free. That run is the headline figure, 0.84 of the set and
0.34 in the exact slot, and it comes with the assumption it rests on measured alongside it,
namely that consecutive shows open with the same song 93% of the time.

**Encore** (`prediction/encore.py`) and **comeback** (`prediction/comeback.py`) each put
several methods in competition: a trained logistic regression and two or three one-line
heuristics. The method that ships is chosen on three non-overlapping validation folds, and the
test window is scored once afterwards. Without that separation, picking the best method off
the test numbers would turn the test set into a training set.

`prediction/selection.py` holds the tie-break. Ranking by the fold mean alone is not enough
when the gap between the top two is smaller than the scatter between folds, which is what
happens on the comeback task, where the trained model leads the recency rule by 0.1 points
across folds that vary by 10. So where a simpler method is not distinguishable from the leader,
by a paired per-fold comparison against its own standard error, the simpler one ships. Both
pages show every method's score on every fold and on the test window, including the cases where
the trained model lost, and say which of the two rules decided the choice.

## Tests

Run the full test suite:

```bash
uv run pytest -v
```

All tests pass with zero real network calls: HTTP interactions with setlist.fm, MusicBrainz,
and Wikidata are all mocked using `respx`, so the suite runs fast and reliably without hitting
external APIs.

## Data and legal

This project stores and displays only structural metadata from public APIs: song titles,
dates, venues, tour names, set order (setlist.fm), release dates/duration/genre tags and
title disambiguation (MusicBrainz), and venue capacity where available (Wikidata).

No lyrics, audio, or copyrighted content is redistributed. All APIs' rate limits and terms of
use are respected. For details on rate limiting and retry logic, see the `*_client.py` modules
under `src/undercurrents/ingestion/` and `src/undercurrents/clustering/`.

## Reading what the payloads already contained

Three fields arrived with every setlist.fm response from the first ingest and were never
extracted. `ingestion/backfill.py` walks the stored `raw_responses` and fills them in, with
no network call at all:

```bash
uv run python -c "import sqlite3; from undercurrents.ingestion import backfill; \
  c=sqlite3.connect('data/undercurrents.db'); c.row_factory=sqlite3.Row; print(backfill.backfill(c))"
```

**City coordinates**, present for 766 of 767 shows. These replace a Nominatim geocoding run
that queried 236 cities at one request per second for something already on disk, and they
cover more venues than it did. Nominatim now only matters for whatever the payloads omit.

**Set names**, 1,217 song rows across 11 distinct segments once spelling is unified: Main
Stage, B-Stage, Acoustic, and on two nights an album title, which marks a record played end
to end. `normalize.canonical_set_name` unifies spelling only, never meaning.

**Guest credits**, 12 appearances with MusicBrainz ids, from Wayne Coyne in 2013 to Dua Lipa
and JENNIE in 2026.

## Performance notes

`derived/notes.py` sorts the 536 free-text notes on individual performances into flags:
debut, long-awaited return, jam, snippet, reprise, instrumental, partial, solo, fan request,
dedication. Each flag stores the phrase that triggered it, so a misclassification can be
traced rather than taken on faith.

`verify_debuts` is the part worth keeping. The notes claim a live debut 70 times; the
function checks each claim against the performance history and reports 60 confirmed and 10
contradicted. It earned its place immediately: the first version of the debut pattern also
matched "first time played *since* 2015", which is the opposite claim, and the check caught
17 returns being scored as debuts.

## Audio features

`clustering/audio_features.py` fetches tempo, key, mode, loudness and danceability from
AcousticBrainz, which is free and needs no key.

The lookup is two-stage on purpose. AcousticBrainz is indexed by MusicBrainz *recording*, and
a song has many recordings; querying only the single stored mbid resolved 43 of 81 songs and
missed Elephant, Let It Happen and The Less I Know the Better, three of the most played
things in the catalogue, all of which are analysed under a different recording id. Searching
every recording of a title raised performance coverage from 45% to 88%. The recording
actually used is stored beside the numbers, because a tempo for one recording of Elephant is
not the same claim as a tempo for Elephant.

AcousticBrainz stopped accepting analyses in 2022, so the 2025 album will never appear there.
That is why coverage is reported both by song (52%) and by performance (88%).

## Weather and venue type

`clustering/weather.py` pulls daily weather for every show from Open-Meteo's archive, and
`clustering/venue_profile.py` adds venue type and opening year from Wikidata alongside the
existing capacity query. The type resolves for 126 venues against capacity's 124, so it is
not better covered as expected, but it carries the distinction that makes the weather usable
at all: 41 of the typed venues are outdoors. On the outdoor shows measured so far, rain makes
no difference to setlist length, and the sample is far too small to conclude otherwise.

## Shows, records, show types and listening

Four more enrichment steps, each safe to re-run:

```bash
uv run python -m undercurrents.clustering.albums        # song -> record, MusicBrainz release groups
uv run python -m undercurrents.clustering.popularity    # ListenBrainz listeners per song
uv run python -m undercurrents.derived.cli build        # also rebuilds show_format (festival / headline / DJ set / TV / incomplete)
uv run python -m undercurrents.prediction.cli train-models --with-sequence   # also writes replay.json and show_type_backtest.json
```

- **Replay** (`prediction/replay.py`): the setlist model walked forward over the archive, refitted every 25 shows on earlier shows only, after a 60-show warm-up. It feeds the Shows explorer ("what the model said the night before") and the Model Health page (calibration, Brier score, accuracy by year against a popularity baseline). The frozen production model is never used to grade past shows.
- **Records** (`clustering/albums.py`): only original editions count, so deluxe, Japanese and anniversary bonus tracks do not pull songs into the wrong era; a song found only on a reissue is typed `Bonus`. Songs left unmatched are unreleased jams and covers.
- **Show types** (`derived/show_format.py`): an estimate, not a label. Every festival call lists the signals behind it (venue name and type, the setlist note, a short set next to nearby shows, a two-weekend repeat). `prediction/show_type.py` then predicts whether the next show is a festival slot, picking between a base rate, "same as last show" and a logistic regression on validation folds.
- **Listening** (`clustering/popularity.py`): ListenBrainz users are a self-selected sample that leans towards long-time listeners, so these counts rank songs relative to each other and are not streaming figures.
