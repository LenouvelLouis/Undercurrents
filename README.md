# Undercurrents

A multi-agent system exploring 18 years of Tame Impala setlists. This project ingests structural data from setlist.fm and MusicBrainz (approximately 750 setlists spanning 2008 to 2026), applies clustering for pattern discovery, predicts song appearances in upcoming performances, and provides a natural-language interface over the band's live history, all presented through a psychedelic and retro-futuristic web UI.

**Status:** Phase 0 (ingestion) implemented. See the project's internal notes for the full phase roadmap.

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
titles via MusicBrainz and compute the setlist/song clustering:

```bash
uv run python -m undercurrents.clustering.cli run
```

This desambiguates song titles (MusicBrainz + a manual alias table for spelling variants and
non-song entries like intros/jams), then clusters setlists and songs into a 2D embedding
stored in `data/undercurrents.db` (`setlist_clusters`, `song_clusters` tables). Add
`--force-refresh` to re-resolve every title and recompute every cluster from scratch, and
`--db-path` to use a different database file.

## Running the prediction agent

Once `data/undercurrents.db` has clustering data from Phase 1, rank songs by likelihood of
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
predictions (N = the number of songs actually played that night).

## Tests

Run the full test suite:

```bash
uv run pytest -v
```

All 40 tests pass with zero network calls: HTTP interactions are mocked using respx, ensuring tests run fast and reliably without hitting external APIs.

## Data and legal

This project stores and displays only structural metadata from public APIs: song titles,
dates, venues, tour names, and set order from setlist.fm. A later phase will add MusicBrainz
for song title disambiguation; it is not yet integrated.

No lyrics, audio, or copyrighted content is redistributed. Both APIs' rate limits and terms of
use are respected. For details on rate limiting and retry logic, see
`src/undercurrents/ingestion/setlistfm_client.py`.
