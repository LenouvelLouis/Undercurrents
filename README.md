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
