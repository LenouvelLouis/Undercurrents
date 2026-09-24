# Undercurrents

Portfolio project analyzing 18 years of Tame Impala setlists (setlist.fm and MusicBrainz,
~750 setlists 2008-2026): data cleaning, clustering, and classical ML prediction over
live-performance history, presented through a psychedelic/retro-futuristic web UI with
separate tabs per capability (not a chatbot).

A natural-language chat agent (Ollama-based orchestrator) was built and validated end-to-end
in Phase 3, then deliberately removed on 2026-09-12 to refocus on data analysis and classical
prediction — see "Phase 3" under Phase status below. It may come back later as a separate
addition, not as the primary interface.

## Git workflow

The agent (Claude Code or any AI assistant working in this repo) never commits or pushes.
It edits files and reports what changed; the human reviews and commits manually, to keep
history intentional.

## Development approach

Work proceeds phase by phase, each with a design spec (`docs/superpowers/specs/`) and an
implementation plan (`docs/superpowers/plans/`) before code is written.

### Phase status

- **Phase 0 (Setup and ingestion)**: implemented. Spec:
  `docs/superpowers/specs/2026-09-12-phase0-ingestion-design.md`. Plan:
  `docs/superpowers/plans/2026-09-12-phase0-ingestion.md`. 40 tests passing; a real ingestion
  run against the live API (and capturing a few real fixtures) is still pending, see the
  plan's closing notes.
- **Phase 1 (MusicBrainz cleanup and clustering)**: implemented. Spec:
  `docs/superpowers/specs/2026-09-12-phase1-clustering-design.md`. Plan:
  `docs/superpowers/plans/2026-09-12-phase1-clustering.md`. A real run against the live
  MusicBrainz API succeeded: 81/157 titles resolved, 632/767 setlists clustered into 42
  coherent per-era clusters (7.6% noise); see the plan's "Real run results" section for
  details, including an operational MusicBrainz-503 issue found and fixed during that run.
- **Phase 2 (Prediction agent)**: implemented. Spec:
  `docs/superpowers/specs/2026-09-12-phase2-prediction-design.md`. Plan:
  `docs/superpowers/plans/2026-09-12-phase2-prediction.md`. A real backtest against
  `data/undercurrents.db` succeeded: 91.0% mean top-N accuracy vs. a 48.6% naive
  global-frequency baseline; top real predictions are plausible in-rotation songs (Elephant,
  Apocalypse Dreams, Feels Like We Only Go Backwards...). See the plan's "Real run results".
- **Phase 3 (Orchestrator and narrative agent)**: implemented and validated against a real
  Ollama instance (91.0%-accuracy predictions correctly surfaced in chat, honest fallback on
  off-topic questions), then **reverted** on 2026-09-12 to refocus on classical data analysis
  and prediction with a dedicated UI instead of a chatbot. Design record kept for reference,
  not currently implemented: `docs/superpowers/specs/2026-09-12-phase3-orchestrator-design.md`,
  `docs/superpowers/plans/2026-09-12-phase3-orchestrator.md` (both marked reverted at the top).
  May be reintroduced later as a separate addition.
- **Phase 4 (Frontend)**: implemented. Spec: `docs/superpowers/specs/2026-09-14-phase4-frontend-design.md`.
  Plan: `docs/superpowers/plans/2026-09-14-phase4-frontend.md`. See "Phase 4 (Frontend) —
  implemented" below.
- Phase 5 (Packaging and demo): not started.

## Phase 0 decisions

- Package/env management: `uv`, Python 3.12.
- Storage: single SQLite database (`data/undercurrents.db`, gitignored) holding both the raw
  API response cache (`raw_responses`) and the normalized schema (`artists`, `tours`,
  `venues`, `setlists`, `songs`, `setlist_songs`). See the Phase 0 spec for the full schema.
- MusicBrainz integration (title disambiguation) is deliberately deferred to Phase 1. Phase 0
  only needs Tame Impala's own artist identifier, resolved dynamically via setlist.fm's own
  `/search/artists` endpoint (not a MusicBrainz call) and cached like any other request.
- HTTP: `httpx` for the client, `respx` to mock it in tests. No real network calls happen in
  the test suite.
- Validation boundary: raw setlist.fm JSON is parsed into Pydantic models
  (`ingestion/raw_schema.py`) at the point it enters the system; everything past that point
  (`ingestion/models.py` normalized dataclasses) is trusted internal data.
- Within a successfully-fetched page, a single malformed setlist entry is logged and skipped
  rather than failing the whole page.
- HTTPS requests use `truststore` (the OS certificate store) instead of the bundled certifi CA
  list, needed on machines behind a corporate proxy or custom CA; same reason `uv` needs
  `native-tls = true` in `pyproject.toml`. Harmless on unrestricted networks.
- `schema.sql` uses `CREATE TABLE IF NOT EXISTS` so re-running the CLI against an existing
  `--db-path` never crashes. Known limitation: there is no migration mechanism yet, if a future
  phase changes a table's columns, an existing `.db` file keeps the old shape silently. Add a
  real migration step (e.g. `PRAGMA user_version` plus versioned migration scripts) before
  changing any existing table.
- A real ingestion run against the live API succeeded: 767 setlists, 2008-08-15 to
  2026-09-11, 8 tours, 157 distinct songs, no malformed entries or failed pages encountered,
  confirming `raw_schema.py` matches the actual setlist.fm response shape.

## Phase 1 decisions

- Title desambiguation: MusicBrainz recording search (`songs.mbid`) plus a hand-curated
  `clustering/aliases.py` for the handful of titles the API won't resolve on its own (spelling
  variants, one Unicode-apostrophe inconsistency). See the Phase 1 spec's Context section for
  how each entry was found.
- Song merging is non-destructive: `songs.canonical_song_id` self-references another row
  instead of deleting/rewriting `setlist_songs` foreign keys.
- Clustering targets: setlists (primary deliverable) by binary song-vector → UMAP → HDBSCAN;
  songs (secondary) by co-occurrence-vector → UMAP → HDBSCAN. Coordinates are stored once with
  a fixed random seed (not recomputed per time window), so a future Phase 4 animation can
  reveal points chronologically without them jumping around.
- `scikit-learn`'s native `HDBSCAN` (>=1.3) is used instead of the standalone `hdbscan` PyPI
  package, since sklearn ships prebuilt Windows wheels and avoids a native build step.
- UMAP's default "spectral" initialization fails on very small inputs (fewer than 5 samples,
  a scipy sparse-eigensolver limitation, not a real-data concern at ~150-750 rows);
  `embeddings.py` falls back to `init="random"` below that threshold.
- A real run against the live MusicBrainz API hit a 503 ("server currently busy") partway
  through resolving titles, after two full resolution passes were run back-to-back (once
  against a test copy of the database, then immediately against the real one) — well within
  MusicBrainz's documented 1 req/s limit, but their public server load-sheds under real-world
  load regardless. Fixed two ways: `title_resolution.resolve_song_titles` now catches
  `MusicBrainzError` per song and logs+skips rather than aborting the whole run (that song
  just stays unresolved and is retried on the next run, same as any other unresolved song —
  mirrors Phase 0's per-page resilience in `fetch_and_store_all_setlists`); and
  `MusicBrainzClient`'s default rate limit was lowered from 1 req/s to 1/1.5s for headroom.
  The run itself needed no manual recovery: already-resolved songs were committed
  incrementally, so re-running picked up exactly where it left off.

## Phase 2 decisions

- One shared `sklearn.linear_model.LogisticRegression` is trained on (setlist, canonical
  song) pairs across the whole history, not one model per song — a per-song model would be
  under-trained for rarely-played songs.
- Features are computed walk-forward via `prediction/features.py`'s `RunningStats`
  accumulator: every feature for a given setlist reflects only setlists strictly before it,
  so training/backtesting can't leak future information into a prediction.
- Known limitation: `cluster_frequency` reuses Phase 1's `setlist_clusters`, which were
  computed once over the *entire* dataset — so backtesting against them carries mild
  lookahead bias (a setlist's cluster assignment was shaped by later setlists too). Accepted
  for this phase; a fully walk-forward re-clustering pipeline is out of scope.
- The model is retrained on demand for every `predict_next_show`/`evaluate` call, never
  serialized — training on ~600 setlists takes well under a second, so persistence would add
  staleness risk without a measurable performance benefit.
- "Agent" here means a well-encapsulated class (`PredictionAgent`) with a clear query
  interface, not a generic inter-agent message-passing protocol — that's introduced in
  Phase 3 once there's a second agent to actually coordinate with.

## Phase 3 (reverted) — see spec/plan docs for full detail

Built and validated for real, then removed on 2026-09-12 per a scope decision to focus on
classical data analysis/prediction with a dedicated UI rather than a chatbot. Kept here only
as a pointer in case it's revisited: local Ollama (`llama3.1:8b`), deterministic keyword-based
intent routing (not LLM-driven — the model only ever phrased answers from data already
retrieved by plain Python), a minimal `RetrievedFacts`-based hand-off between retrieval and
narration. Full rationale is preserved in the (reverted) spec and plan docs referenced above.

## Feature enrichment (2026-09-12, post-Phase-3-revert)

Four additional data dimensions were added on top of Phases 0-2's existing tables, in order,
each verified against real data before moving to the next:

1. **Positional prediction features** (`prediction/agent.py`): `predict_opener_probability`
   and `predict_closer_probability` alongside the existing `predict_encore_probability`, all
   three now sharing a `_play_count_matching` helper that's canonicalization-aware (a bug
   found while adding this: `predict_encore_probability` previously queried a song's own
   `setlist_songs` rows directly, missing plays recorded under a merged variant's id — fixed
   via `clustering/features.py`'s new public `variant_song_ids`, now also used by
   `orchestrator`-era `facts.last_played_date`'s replacement logic). Also added to
   `clustering/stats.py`: `show_number_in_tour` (1-indexed chronological position within a
   tour) and `average_setlist_length_by_year` (excludes setlists with zero `setlist_songs`
   rows — a Phase 0 data gap, not a real 0-song show). Real-data check: average length grows
   from ~3-4 songs/show (2008-2009 clubs) to ~17-22 (2021-2026 headline/festival slots);
   "Intro" opens 98.9% of its plays; "Elephant" almost never opens/closes (a mid-set anthem).
2. **MusicBrainz metadata enrichment** (`clustering/enrichment.py`): for songs already
   resolved to an MBID (Phase 1), a follow-up `/recording/{mbid}?inc=releases+genres+tags`
   lookup fills `songs.release_date` (earliest of the recording's releases), `duration_ms`,
   and `genre_tags` (JSON array, `genres` falling back to `tags` if empty). Same per-song
   `MusicBrainzError` resilience as `title_resolution.py`. Real run: 80/81 resolved songs
   enriched (1 skipped on a transient 503, retried automatically next run — the Phase 1
   per-song resilience fix paid off here unmodified). Two caveats found and documented rather
   than "fixed" (they're real properties of the data, not bugs): `release_date` is the release
   date of *that specific MusicBrainz recording*, which may be a later remaster/reissue, not
   necessarily the song's true first release; `genre_tags` reflects MusicBrainz's crowdsourced
   folksonomy and can be noisy (e.g. "euro house" attached to a psych-rock track).
3. **Geographic touring cadence** (`clustering/geography.py`): `country_show_count`,
   `days_since_country_last_visited`, `days_since_continent_last_visited` (both cutoff at a
   `reference_date`, consistent with Phase 2's leakage-free style), backed by a hand-verified
   country→continent map (`COUNTRY_TO_CONTINENT`) covering all 39 countries actually present
   in the real data. Venue-to-venue distance (would need geocoding) was scoped out — no
   reliable bundled coordinate source was available without adding a real dependency.
4. **Venue capacity** (`clustering/venue_capacity.py` + new `clustering/wikidata_client.py`):
   conservative Wikidata matching — exact venue-name label match, country cross-checked
   against a verified `COUNTRY_QIDS` map (looked up via a real SPARQL query against Wikidata,
   2026-09-12), candidates whose description looks historical/defunct filtered out, and
   *zero or multiple* remaining matches both resolve to "unknown" rather than guessing (e.g.
   the real "Madison Square Garden" search returns 3 defunct arenas sharing the exact name —
   description filtering + country/capacity checks correctly isolate the current one, but the
   code deliberately gives up rather than picks arbitrarily whenever it can't). **Superseded (2026-09-18): the TLS-fingerprint diagnosis below was wrong.**

   The original note recorded this as a blocker: Wikimedia's edge returned 403 "robot policy"
   to `httpx` while `curl` succeeded, which was read as a TLS/client-fingerprint check. Two
   findings replace that:

   1. **It was the User-Agent, not the TLS stack.** Wikimedia's user-agent policy asks for a
      contact the operator can reach, and the 403 body points at that policy. The old UA
      (`"Undercurrents/0.1 ( personal non-commercial research project )"`) named no contact.
      Adding the public repository URL made identical `httpx` requests return 200. `curl`
      appeared to work earlier because it was tried at low volume, not because of its TLS
      stack.
   2. **Per-venue search does not scale, and should not.** Even with a compliant UA, 556
      venues at roughly two API calls each is over a thousand requests, and the edge is right
      to refuse that. The fix was to stop asking that way: `clustering/venue_capacity_bulk.py`
      sends batches of a hundred venue labels to the SPARQL endpoint, which is the interface
      Wikimedia documents for bulk reads. Six requests replaced eleven hundred.

   Coverage is now 124 of 556 venues. The remainder is not a bug: matching stays deliberately
   conservative, accepting a name only when it resolves to exactly one capacity within the
   venue's own country, across both `rdfs:label` and `skos:altLabel`. "Olympia" alone matches
   four Wikidata entities with capacities from 10 to 16000, so an ambiguous name is left unset
   rather than guessed at. The per-venue module is kept for single lookups; the bulk path is
   what a full run should use.

## Feature enrichment round 2 (2026-09-12)

A further 11 additions, each verified against real data before moving to the next:

1. **Setlist-level `info` field** (Phase 0 gap fix): setlist.fm's schema has a per-concert
   `info` field distinct from the per-song one already captured — `RawSetlist` never declared
   it, so it was silently dropped since Phase 0. Now captured end-to-end (`raw_schema.py` →
   `normalize.py` → `models.py` → `setlists.info`, retrofitted via idempotent
   `ensure_setlists_info_column`). Real re-ingestion from cache (no new network calls)
   populated 105/767 setlists — genuinely rich content ("Live debut of Currents material",
   "Show was cancelled due to lightning storm", "Setlist incomplete and out of order").
2. **`clustering/annotations.py`**: deterministic keyword mining of both `info` fields —
   per-song flags (`is_debut`, `is_fan_request`, `has_tease`, `was_extended`,
   `was_restarted`) and per-setlist flags (`is_incomplete`, `is_out_of_order`,
   `was_disrupted`). Real counts: 107 song debuts, 39 extended outros, 38 incomplete
   setlists — all plausible against manual spot-checks of the source text.
3. **MusicBrainz work-based release dates** (`clustering/enrichment.py`): a resolved
   recording's linked "work" entity can connect to *other* recordings of the same song
   (different masters/remasters); `_find_related_studio_recording_ids` fetches up to
   `MAX_RELATED_RECORDINGS` (5) non-live-looking ones and takes the overall earliest release
   date across all of them, fixing the "wrong specific recording" caveat from round 1. Real
   check: "Apocalypse Dreams" moved from an incorrect 2014 (a later live recording's release)
   to the correct 2012 (its actual Lonerism-album year).
4. **`clustering/calendar_features.py`**: `is_holiday`/`nearest_holiday_distance_days` via the
   `holidays` package (new dependency, fully offline). Country names stored in `venues` match
   the package directly for 35/39 real countries; the 4 exceptions (`United States`,
   `New Zealand`, `United Kingdom`, `Hong Kong SAR China`) are mapped to their ISO code in
   `COUNTRY_NAME_OVERRIDES` — verified individually against `holidays==0.104`. Real check:
   14/767 shows landed on a recognized public holiday in their country.
5. **Venue-level return frequency** (`clustering/geography.py`): `venue_show_count` /
   `days_since_venue_last_visited`, the same pattern as round 1's country/continent versions
   but at exact-venue granularity.
6. **`clustering/stats.py`: `average_relative_position`** — position ÷ setlist length,
   comparable across eras of very different typical setlist length. Real check: "Intro"
   averages 0.07 (near the start, as expected), "New Person, Same Old Mistakes" averages
   0.946 (matches its known role as the band's customary closer).
7. **Tour leg segmentation** (`clustering/stats.py`): `tour_leg_number` /
   `show_number_in_leg`, splitting a tour into legs wherever the gap between consecutive
   shows exceeds `LEG_GAP_THRESHOLD_DAYS` (14). A pure date-gap heuristic — it won't always
   match the band's own informal "leg" numbering, but real data confirms it correctly finds
   the real touring-break boundaries (e.g. the ~4.5-month gap between the Deadbeat tour's
   North American and 2026 legs).
8. **Song transition matrix** (`clustering/features.py`): `build_song_transition_matrix`
   counts directed immediate-adjacency transitions (song A played right before song B),
   distinct from round-1's same-setlist co-occurrence. Excluded songs (intros/jams) are
   filtered out *before* computing adjacency, so they act as invisible connective tissue
   rather than breaking a transition between the two real songs around them. Required adding
   `position` to `db.get_setlist_song_entries`'s existing query (backward-compatible, no
   caller relied on the column list being exactly `setlist_id, song_id`). Real check:
   Elephant's most common next song is "Feels Like We Only Go Backwards" — a well-known segue.
9. **Consecutive-setlist similarity** (`clustering/stats.py`): `consecutive_setlist_similarity`
   computes the Jaccard index between each setlist's song set and its chronological
   predecessor's, reusing `build_setlist_song_matrix` rather than re-deriving the
   canonicalized/filtered song set a third time. Real check: similarity trends from ~0.40
   (2008, small early club sets) up to ~0.85 (2019, mature/standardized setlists), with a
   sharp dip in 2020 (0.207) matching the irregular one-off livestream/pandemic-era shows.
10. **Song streaks** (`clustering/stats.py`): `current_consecutive_streak` (shows in a row
    counting back from the most recent one) and `longest_consecutive_streak` (anywhere in
    history). Real check: Elephant and Apocalypse Dreams are both on 52-show current streaks;
    "Intro" and any `excluded_from_clustering` song correctly returns 0 (outside the filtered
    song universe used by `build_setlist_song_matrix`, same filtering as everywhere else).
11. **Cluster song entropy** (`clustering/stats.py`): `cluster_song_entropy` — Shannon entropy
    (bits) of each setlist cluster's song-frequency distribution, a "how varied vs.
    predictable" score per era. Real check: the previously-flagged heterogeneous "catch-all"
    cluster 33 (odd assorted rarities, spanning nearly the whole history) has the highest
    entropy (5.83 bits) of any cluster — confirms the metric captures what it's meant to.

Deliberately **not** pursued after research (see chat history / this session for the full
survey): Spotify popularity (their ToS forbids storing it long-term), Wikipedia
attendance/gross figures (coverage too sparse outside stadium-tier acts), Open-Meteo weather
(would need venue geocoding the dataset doesn't have).

## Wiring round-1/2 features into the Phase 2 model (2026-09-12)

`FEATURE_ORDER` in `prediction/model.py` was extended from 5 to 10 features:
`country_frequency`, `current_streak`, `cluster_entropy`, `is_holiday`, `duration_minutes`
alongside the original `global_frequency`, `tour_frequency`, `cluster_frequency`,
`shows_since_last_played`, `days_since_last_played`. `RunningStats` (`prediction/features.py`)
gained matching walk-forward state (`country_setlists`/`country_count`, `current_streak`,
`_current_cluster_entropy`); `duration_minutes` is mean-imputed for songs without a known
duration (`db.get_song_durations_ms`, self-healing). Deliberately **not** wired in:
`average_relative_position`, `song_age_years`, the transition matrix, tour-leg numbering, and
consecutive-setlist similarity — either circular (they describe the very setlist being
predicted, not something knowable in advance) or awkward to fit into the "will song X appear"
per-song binary framing.

**Real backtest result (`data/undercurrents.db`, same train/test split, old 5-feature
`FEATURE_ORDER` vs. new 10-feature one):**

| holdout shows | old (5 features) | new (10 features) | delta |
|---|---|---|---|
| 10 | 91.00% | 90.98% | -0.02% |
| 20 | 90.98% | 91.20% | +0.23% |
| 30 | 90.66% | 90.66% | +0.00% |
| 50 | 89.95% | 89.95% | +0.00% |

The new features are not degenerate (verified real variance, e.g. `cluster_entropy` ranges
0-5.8 bits, `current_streak` 0-76 shows) but add no measurable accuracy on top of the
frequency-based features already in the model — differences are within noise. Likely cause:
the "will song X appear next show" target is already near a predictability ceiling from
frequency/recency alone (Tame Impala's setlists are strongly tour-templated), so secondary
contextual signals (holiday, country, duration, entropy) have little room left to add. Kept in
the model anyway since they're real signal with zero measured downside, and may matter more
for future targets (e.g. predicting *position* or *encore* status) than for "will it appear at
all." No further model tuning (e.g. regularization strength, feature scaling) was attempted —
out of scope for this pass; flagged as a natural next step if prediction accuracy work resumes.

## Setlist length prediction (2026-09-12)

First of four new prediction targets (spec:
`docs/superpowers/specs/2026-09-12-setlist-length-prediction-design.md`, plan:
`docs/superpowers/plans/2026-09-12-setlist-length-prediction.md`). Standalone capability,
deliberately not wired into `predict_next_show`'s top-N cutoff. New module
`prediction/setlist_length.py` mirrors Phase 2's walk-forward architecture
(`LengthStats.observe`/`features_for`, `build_training_rows`, `build_prediction_features`) but
one row per *setlist* with a regression target (`sklearn.linear_model.Ridge`, untuned) instead
of one row per (setlist, song) with a classification target. Length is defined as the raw
`setlist_songs` row count (intros/tape/covers included, matching `clustering/stats.py`'s
`average_setlist_length_by_year`) rather than the canonicalized/filtered song-set count
`predict_next_show` uses — a deliberate choice since this target is independent of the
song-ranking universe. 8 features: `recent_avg_length` (rolling mean of last 5 shows),
`global_avg_length`, `tour_avg_length`, `country_avg_length`, `cluster_avg_length` (via the
same "last observed cluster" trick as Phase 2's `cluster_frequency`), `show_number_in_tour`,
`days_since_last_show`, `is_holiday` (reuses `prediction.features._is_holiday_flag`, no
duplicated logic). `PredictionAgent.predict_setlist_length` and
`evaluate.backtest_setlist_length` added alongside the existing song-prediction methods;
`prediction/cli.py`'s existing `predict`/`evaluate` subcommands print the new numbers too (no
new subcommands, by design — the CLI is a dev tool, not the eventual UI).

**Real result (`data/undercurrents.db`):** MAE 0.85-1.17 songs across holdout sizes 10-50,
against held-out shows averaging ~22 songs (2021-2026 era) — roughly 4-5% relative error, a
strong result. 632/767 setlists have at least one `setlist_songs` row (the rest are the known
Phase 0 transcription gap) and all 632 are used for training/evaluation. Feature variance
checked and non-degenerate on real data (e.g. `show_number_in_tour` ranges 0-168,
`days_since_last_show` 0-804). A real cold prediction (no tour/country hint, today's date)
returned 16.7 songs — plausible against the real recent-era range.

## Position category prediction (2026-09-12)

Second of four new prediction targets (spec:
`docs/superpowers/specs/2026-09-12-position-category-prediction-design.md`, plan:
`docs/superpowers/plans/2026-09-12-position-category-prediction.md`). Added alongside (not
replacing) the existing `predict_opener/closer/encore_probability` — those stay as a simple
all-time-ratio stat; the new `PredictionAgent.predict_position_category` is a walk-forward,
leakage-free, 4-class `sklearn.linear_model.LogisticRegression` (`opener` / `closer` / `encore`
/ `mid`, priority `encore > opener > closer > mid` on overlap — verified against real data that
`closer` and `encore` overlap 56% of the time, but `opener`/`encore` never do). New module
`prediction/position.py`; `db.get_setlist_song_entries` extended with `is_encore` (backward
compatible, same pattern as round 2's `position` addition).

**Real result caught and fixed during verification, not just documented as a limitation:** the
first version (8 features: lifetime `own_*_rate` + `global_*_rate` + `times_played_before` +
`days_since_last_played`) scored 85-87% overall accuracy but **0% opener recall at every
holdout size** — a real defect, not noise. Root cause found by inspecting the actual held-out
opener plays: a song's lifetime `own_opener_rate` badly lags a genuine recent role change (one
real song's last-20-plays opener rate was 65% while its lifetime rate was only 5%, because it
opened almost every show in the current era after rarely opening in its much longer earlier
history). Confirmed this wasn't a feature-scaling artifact first (tried `StandardScaler`, no
change) before diagnosing the real cause. Fix: added `recent_own_opener_rate` /
`recent_own_closer_rate` / `recent_own_encore_rate` (rolling window of the song's own last 20
plays, `RECENT_WINDOW` — same rolling-window pattern as `setlist_length.py`'s
`recent_avg_length`, falling back to the global rate when a song has no prior plays at all),
alongside the original lifetime rates rather than replacing them. Also bumped
`LogisticRegression(max_iter=1000)` to `5000` to clear a persistent convergence warning (the
richer 11-feature model needed more iterations; a real fix, not tuning for accuracy).

**Result after the fix (`data/undercurrents.db`):**

| holdout shows | overall accuracy | opener recall | mid recall | encore recall |
|---|---|---|---|---|
| 10 | 92.9% | 80.0% | 97.6% | 70.0% |
| 20 | 94.5% | 90.0% | 97.1% | 81.7% |
| 30 | 95.3% | 93.3% | 97.9% | 81.3% |
| 50 | 96.4% | 92.0% | 98.0% | 88.1% |

(`closer`, the rarest category, had zero occurrences in these particular holdout windows —
recent-era shows in the real data essentially always end in an encore.) 8458 real plays across
632 setlists (`mid` 6987, `encore` 751, `opener` 468, `closer` 252), all 11 features checked for
real, non-degenerate variance. A real cold prediction correctly called "Elephant" as `mid`
(0.972) — matching the documented real behavior that it "almost never opens/closes" — and
"Apocalypse Dreams" as `opener` (0.835), consistent with a real recent-era opener shift the new
recency feature was built to catch.

## Next show date prediction (2026-09-12)

Third of four new prediction targets (spec:
`docs/superpowers/specs/2026-09-12-next-show-date-prediction-design.md`, plan:
`docs/superpowers/plans/2026-09-12-next-show-date-prediction.md`). Unlike the other two
targets, this one predicts *when* the next show happens rather than a property of an
already-known show date, and uses every real `setlists.event_date` (not filtered by song
content — a show having happened is a real event regardless of whether its setlist was ever
fully transcribed). New module `prediction/next_show_date.py`; `PredictionAgent.
predict_next_show_date(conn, as_of_date=None) -> date`.

Real consecutive-show gaps are extremely right-skewed (median 2 days, p90 15 days, max 804
days/~2.2 years between an album cycle's tours) — verified before designing. `sklearn.
linear_model.Ridge` is trained on `log(1 + gap_days)` (inverted via `expm1()` for the final
prediction) rather than raw days, so the rare huge gaps don't dominate the fit. 6 features via
a self-tracked "touring leg" concept (14-day gap threshold, same constant as `clustering/
stats.py`'s `tour_leg_number` but recomputed leakage-safe from scratch, since that existing
function looks at a tour's full date range): `last_gap_days`, `recent_avg_gap_days` (rolling
window of 5), `current_leg_avg_gap_days`, `show_number_in_current_leg`,
`days_since_leg_started`, `global_avg_gap_days`. Per an explicit decision, a predicted date
implying a show is "overdue" relative to today is returned as-is (even if before today) rather
than clamped to "at least tomorrow" — a real, honest signal, not something to hide.

**Real result (`data/undercurrents.db`):** MAE 1.8-3.3 days across holdout sizes 10-50, but
median absolute error only 0.8-2.1 days — confirming the expected skew (a handful of
held-out shows landing right after a real multi-month gap pull the mean up, same reasoning
behind reporting both rather than MAE alone). 766 real training rows, all 6 features checked
for real non-degenerate variance (e.g. `last_gap_days` ranges 0-804, `show_number_in_current_
leg` up to 41). A real cold prediction: the dataset's last real show was 2026-09-11 (one day
before "today" in this environment), with a recent 2-3 day cadence; the model predicted
2026-09-14 (3 days later) — well calibrated against that visible active-touring context.

## Next show country prediction (2026-09-13)

Fourth and final of the new prediction targets (spec:
`docs/superpowers/specs/2026-09-13-next-show-country-prediction-design.md`, plan:
`docs/superpowers/plans/2026-09-13-next-show-country-prediction.md`). Predicts which country
the next show will be in, using the same shared binary-classifier-over-candidates architecture
as Phase 2's song prediction (`prediction/features.py`/`prediction/model.py`) rather than a
native multi-class classifier, adapted from "one row per (setlist, candidate song)" to "one row
per (setlist, candidate country)". New module `prediction/next_show_location.py`
(`CountryStats` walk-forward accumulator tracking global/tour country frequency, current
country streak, and days/shows since a country was last visited; `sklearn.linear_model.
LogisticRegression`); `PredictionAgent.predict_next_show_country(conn, reference_date=None,
tour_id=None) -> list[CountryPrediction]`. Like `next_show_date.py` (and unlike
`predict_next_show`/`setlist_length.py`), it uses every row in `setlists` regardless of
whether the setlist's songs were ever transcribed, since a show's location is known
independently of its content; only countries already observed at least once before the
setlist being scored are candidates, so a never-yet-visited country gets no score rather than
a hallucinated one.

**Real result (`data/undercurrents.db`):**

| holdout shows | top-1 accuracy | top-3 accuracy |
|---|---|---|
| 10 | 80.0% | 90.0% |
| 20 | 80.0% | 90.0% |
| 30 | 76.7% | 86.7% |
| 50 | 56.0% | 62.0% |

767 real setlists across 39 countries, heavily skewed toward the United States (262 shows)
and Australia (201) as documented in the design spec's real-data survey. Accuracy is strong at
the smaller holdout sizes and degrades at 50 — plausible given the skew: a 50-show holdout
window reaches back further chronologically and catches more of the country-to-country tour
transitions (Europe/Asia legs interleaved with North America/Australia) that a 10- or 20-show
window, sitting entirely inside the current US-heavy touring stretch, doesn't have to predict
across. Top-3 consistently beats top-1 by 6-10 points at every size, confirming the model is
doing more than just always guessing the single most common country.

A real cold prediction (`predict --db-path data/undercurrents.db`) returned top-3 countries
United States (0.715), Australia (0.043), United Kingdom (0.017). Cross-checked against the
database's 10 most recent real shows (`event_date`, `venues.country`): 2026-09-11 United
States, 2026-09-08 United States, 2026-09-06 Canada, 2026-09-05 Canada, 2026-09-02 United
States, 2026-09-01 United States, 2026-08-28 United States, 2026-08-25 United States,
2026-08-05 United States, 2026-08-04 United States — a dominant, ongoing United States leg
with one short Canada detour. The top prediction (United States, well ahead of every other
country) plausibly reflects that real recent touring context.

This is the fourth and final of the four new prediction targets planned in the "Feature
enrichment" work: setlist length, position category, next show date, and next show country are
all now implemented and real-data-verified per this and the three preceding sections. No
further prediction target is currently planned.

## Phase 4 (Frontend) — implemented (2026-09-14)

Spec: `docs/superpowers/specs/2026-09-14-phase4-frontend-design.md`. Plan:
`docs/superpowers/plans/2026-09-14-phase4-frontend.md` (16 tasks). Reproduces the approved
Claude Design mockup: a landing page plus a "Predictions" tab (5 screens) and a "Data Analysis"
tab (5 screens), backed by a new read-only FastAPI layer over the existing
`data/undercurrents.db` — no changes to any existing prediction/clustering/storage module, the
API layer only calls and serializes their already-verified output.

**Architecture:** `src/undercurrents/api/` (FastAPI, one router per domain: `stats`, `songs`,
`predictions`, `analysis`; 12 endpoints total) + `web/` (React 19 + Vite + TypeScript +
Tailwind, dev server proxies `/api/*` to the FastAPI backend). Ten screen components under
`web/src/pages/{predictions,analysis}/`, a shared component library (`TopNav`, `SubTabRow`,
`Card`, `RingGauge`, `ProgressBar`, `StatBar`, `BackgroundGlow`) and a typed `api.ts` client
covering every endpoint. `App.tsx` holds all navigation state (landing/app, active tab,
sub-tab index) — no router library, since there's no need for deep-linkable URLs at this stage.

**Two deliberate deviations from the mockup**, both decided in the spec and implemented as
such, not left unfinished: (1) **Venue Map** is a real sortable table (venue, city, country,
shows, capacity, last visited) instead of a plotted map — the dataset has no venue
coordinates (Phase 1's venue-to-venue distance work was scoped out for the same reason, and
geocoding was never added); the honest caption says so directly rather than faking a map.
(2) **Next Date** shows mean/median absolute error stats instead of a second "typical date"
figure — no real historical median date exists to display; showing the model's real
backtested error bars is more honest than inventing one.

**Real verification:** full backend suite green (308 tests). Browser walkthrough of all 11
screens against `data/undercurrents.db` confirmed real numbers matching every prior
documented result in this file: Next Setlist top-3 (Apocalypse Dreams, Elephant, Feels Like We
Only Go Backwards, all ~99%) and 143 candidate songs; Concert Length 16.7 songs; Song Role for
"Elephant" (mid 97%, opener 2%, encore 1%, closer 0%, matching the "almost never opens/closes"
note above); Next Date predicted 2026-09-14 with 2.6/0.9 day mean/median error; Next Country
led by United States at 71%, Australia 4%, United Kingdom 2%; Venue Map's real venues sorted by
show count; Setlist Trend's line rising from ~3-4 to ~17-22 songs/show across era bands with
the 2020 pandemic dip visible; Cluster Explorer's orbit view and detail panel; Transition
Graph defaulting to Elephant → Feels Like We Only Go Backwards (15%, top follow-on); Anecdotes
timeline sorted newest-first with colored tag pills. No console errors, no broken layouts.

**How to run:** see the README's "Running the web app" section —
`uv run uvicorn undercurrents.api.app:app --reload --port 8000` plus `cd web && npm run dev`.

## Frozen model caching (2026-09-16)

Spec: `docs/superpowers/specs/2026-09-16-frozen-model-caching-design.md`. Plan:
`docs/superpowers/plans/2026-09-16-frozen-model-caching.md`. A performance change to the Phase 4
API layer only — no change to any prediction/clustering module's actual logic or output. Every
`/api/predictions/*` endpoint previously retrained its scikit-learn model from scratch on every
request (fast per call, well under a second, per Phase 2's original decision — but one endpoint,
`/next-date`, compounded this into a real bottleneck by also re-running a full 10-fold backtest
on every request just to report MAE/median stats).

**Architecture:** `PredictionAgent.predict_*` methods (`prediction/agent.py`) gained an optional
`trained_model=None` parameter — skips training when supplied, unchanged default behavior
(always retrains) otherwise, so `evaluate.py`'s walk-forward backtesting keeps retraining at
every historical cutoff exactly as before. New `prediction/frozen_store.py::FrozenModelStore`
implements a three-tier cache (in-memory → `data/models/*.joblib` on disk → train-and-persist)
supplying that parameter to `api/predictions.py`'s router, plus the same caching for
`/next-date`'s backtest stats (`next_date_backtest.json`). A new
`uv run python -m undercurrents.prediction.cli train-models` command forces a full retrain —
this is the only place retraining happens once artifacts exist; it's meant to be rerun manually
after an ingestion session adds data (deliberately not auto-triggered by the ingestion CLI, an
explicit scope decision made during design). `data/models/` needed no new `.gitignore` entry —
covered by the existing blanket `data/` rule.

**Known limitation, documented not solved:** no compatibility check between a frozen `.joblib`
and the code that produced it — a future change to any predictor's feature order will make a
stale frozen model raise at scoring time; recovery is deleting `data/models/` and rerunning
`train-models`. Same category as the pre-existing undocumented-migration caveat on `schema.sql`
(Phase 0 decisions, above). Also: a running API process's in-memory cache doesn't see a
`train-models` run from another process until restarted — acceptable, since ingestion itself is
already a manual multi-step workflow.

**Real verification:** full suite green (320 tests). Ran `train-models` against
`data/undercurrents.db` (9.4s — one-time cost, amortizing what used to be paid on every request);
confirmed all 5 `.joblib` files + `next_date_backtest.json` + `metadata.json` written. Started
the real API and hit every `/api/predictions/*` endpoint: all returned in 39-63ms (previously
un-timed per-request, but necessarily bounded below by the 9.4s full-retrain cost this now
amortizes away). Predictions matched every already-documented real result unchanged — Next
Setlist top-3 (Apocalypse Dreams/Elephant/Feels Like We Only Go Backwards, ~99%), Concert Length
16.7 songs, Song Role for Elephant (mid 97.2%/opener 1.5%/encore 0.96%/closer 0.34%), Next Date
2026-09-14 with 2.6/0.9 day mean/median error, Next Country led by United States at 71.5% —
confirming freezing changed serving speed, not the underlying predictions.

## Data provenance and scope

Only structural metadata from public APIs (setlist.fm, MusicBrainz) is stored or displayed:
song titles, dates, venues, tour names, set order. No lyrics or audio are redistributed.
Rate limits of both APIs are respected (see `ingestion/setlistfm_client.py` for the throttling
and retry/backoff logic).

## Running the ingestion pipeline

```bash
uv sync
cp .env.example .env   # then fill in SETLISTFM_API_KEY
uv run python -m undercurrents.ingestion.cli fetch
```

Add `--force-refresh` to bypass the cache and `--db-path` to write elsewhere than the default
`data/undercurrents.db`.

## Tests

```bash
uv run pytest -v
```


## Round 3: derived features, heatmaps, geocoding and model benchmarks (2026-09-18)

Four additions, each verified against the real database before moving on.

**Derived feature tables** (`undercurrents/derived/`). `song_features` (124 rows) and
`setlist_features` (632 rows), rebuilt from scratch by `python -m undercurrents.derived.cli
build`. Per song: plays, shows, first/last played, longest absence, current streak, opener /
closer / encore / cover counts, average normalised position, dominant era. Per show: song
count, encores, covers, tapes, opener and closer, summed known duration and whether that
sum is complete, novelty against the previous show, days since it, and travel distance.
Every column is a recomputation of ingested rows, so the rebuild is idempotent; `rebuild`
truncates and refills both tables. Tape entries are excluded from song counts (matching the
length model) but counted separately in `tape_count`, so the exclusion stays visible.

**Venue geocoding** (`clustering/geocode.py`). Latitude/longitude for 549 of 556 venues via
Nominatim, one lookup per distinct (city, country) rather than per venue, which cut 556
requests to 236. Serial, 1.1s apart, repository URL in the UA, per their usage policy.
Coordinates are the venue's *city*, not the building: venue names resolve badly on their own
and the point of these coordinates is measuring how far the band travelled, which city-level
precision answers. 628 of 632 legs now have a distance: 1,320,399 km total, 2,103 km average
hop, 18,986 km longest. Distances are great-circle, so a floor rather than routed mileage.

**Heatmaps** (four endpoints under `/api/analysis/heatmap/`). Songs by year, month-by-year
touring calendar, songs by normalised set position, and the song co-occurrence matrix. All
plain cross-tabs of `setlist_songs`. The front end renders them on one sequential ramp
(single hue, monotonic in OKLab lightness, square-root scaled because play counts are
heavily skewed) with a legend and per-cell hover, never a rainbow.

**Model benchmarks** (`undercurrents/benchmarks/`, `python -m undercurrents.benchmarks.cli
run`). Three experiments, each against the simplest thing that could work, on a strictly
chronological split (the 60 most recent shows held out; never random). Results are written
to `data/models/benchmarks.json` and served read-only at `/api/predictions/benchmarks`,
because training per request would be absurd and a stored file keeps the app's numbers
identical to a dated run.

| Experiment | Baseline | Model | Result |
|---|---|---|---|
| Next song in the set | first-order Markov, top-1 0.285 | GRU (64/128, 60 epochs), top-1 0.676 | **model, +39.0 points** |
| Will a song be played | logistic regression (in production), F1 0.889 | MLP (64,32), F1 0.901 | model, +1.2 points |
| Song embeddings | (none) | item2vec, 48d, 111 songs | representation only |

The sequence result was the surprise and is worth keeping in mind: setlists are *structured*,
not merely repetitive, so the full prefix of tonight's set carries far more signal than its
last song alone. Both models are blocked from predicting a song already played that night, so
neither is flattered by a constraint the other lacks. The MLP result is the expected one: with
~29k rows and ten well-chosen features, extra capacity buys little, and the gain is almost
entirely recall.

## Round 4: sequence and rotation predictions (2026-09-18)

Three predictions added beyond the original five, and two findings that matter more than the
code.

**The measurement protocol changed for the last two.** `encore.py` and `comeback.py` each put
a trained logistic regression up against one-line heuristics. The method that ships is chosen
on a validation window and only then scored on a test window it never touched. This was not
academic caution: the first pass picked the winner straight off the test numbers, and the
trained model looked like it won both tasks by large margins. Under the two-window protocol
the picture changed, and the honest results are below. Anyone extending this should keep the
separation. Reading the winner off the test set is the easiest way to ship a model that looks
better on the page than it is on the night.

**The selection rule was tightened again (`prediction/selection.py`).** One validation window
turned out to be too noisy to decide anything. Moved to three non-overlapping folds of 40
shows, and the picture changed completely: across folds the trained model beats the recency
heuristic by 1.6 points on the encore task and by **0.1 points** on the comeback task, while
the folds themselves vary by 10 to 14 points. Calling the model the winner on a 0.1-point mean
is a coin landing heads, not a measurement.

So the rule now has a second stage. Rank by the fold mean, then, where a simpler method is not
*distinguishable* from the leader, take the simpler one. Distinguishable means the paired
per-fold difference has a mean larger than its own standard error. Both stages are fixed
before any test number is looked at, and preferring simplicity on a tie is a standing
engineering preference rather than a reading of the data, which is what keeps it out of the
test window.

It discriminates rather than just always picking the simple thing: on the comeback task the
0.1-point lead is rejected and the recency rule ships (and then wins the test window by 2.6
points); on the encore task the model is ahead on every single fold and is kept (and then
loses the test window by 3.3 points). That second outcome is left standing and printed on the
page. Three folds of 181 encore slots is not enough to resolve a 3-point difference, and
pretending otherwise by re-picking after seeing the test set is the exact failure the protocol
exists to prevent.

**Finding 1: this band's setlist is recency-driven, not history-driven.** Ranking encore
candidates by lifetime encore count scores 0.243. Ranking them by what was encored in the
last ten shows scores 0.917. The same holds for returns: base rate 0.147, last-ten-shows
0.692. Any future feature work on setlist prediction should weight short windows heavily and
treat lifetime aggregates as near-useless.

**Finding 2: "overdue" is a fan myth.** Ranking shelved songs by how overdue they are against
their own historical gap scores 0.0065 on validation and 0.0 on test, against a 0.046 base
rate for a candidate returning at all. Songs are not owed a comeback. The page says so.

| Prediction | Chosen method | Fold mean | Test score | Runner-up on test |
|---|---|---|---|---|
| Encore | logistic regression, kept (ahead on all 3 folds) | 0.830 | 0.884 | last-ten-shows 0.917, so the choice cost 3.3 points |
| Comeback | last-ten-shows, kept on the simplicity tie-break | 0.561 | 0.692 | logistic regression 0.667 |

**Running order, and the finding that made the page work.** `running_order.py` productionises
the benchmark GRU: it writes the set in order rather than ranking the catalogue. The gap
between decoding regimes is the thing to understand before touching it.

| Seed given to the model | Songs recovered | In the exact slot |
|---|---|---|
| nothing | 0.323 | 0.023 |
| the real first song | 0.891 | 0.364 |
| the real first 3 | 0.838 | 0.322 |
| the real first 5 | 0.820 | 0.243 |
| **the previous show's first 3** (what the page does) | **0.841** | **0.341** |
| static most-played list, for reference | 0.453 | 0.024 |

One real opening song is worth 57 points. That is what saved this feature: free-running from
nothing the GRU loses to a leaderboard, so the first version of the page would have been
worse than useless. The page works because the previous show's opening is a good enough
stand-in, and it is good enough for a reason that is itself measurable: consecutive shows open
with the same song 93.2% of the time. If that ever stops being true, this page degrades
towards the 0.323 row, so the number is computed by the backtest and displayed, not hardcoded.

Note the accuracy *falls* as the real seed lengthens (0.891 at one song, 0.820 at five). The
early set is the predictable part; a longer seed spends that predictability and leaves the
harder tail to guess.

Training takes about three minutes, so the bundle is always loaded from
`data/models/running_order.joblib`; only the state dict and vocabulary are stored, never a
live torch object. `train_all` deliberately does not fit it: that stayed a sub-second call, and
the slow work moved to `train_slow`, behind `train-models --with-sequence`.

A note for later: `schema.sql` now declares `capacity`, `latitude` and `longitude` on
`venues`. They used to exist only as `ALTER TABLE` migrations, which meant a fresh database
(every test database) lacked them and anything joining on coordinates broke. Migrations are
still there for existing databases; new columns should go in both places.

## Round 5: reading the payloads properly, audio features, weather (2026-09-19)

**The geocoding run was unnecessary and this is the lesson to carry.** setlist.fm ships city
coordinates with every setlist, for 766 of 767 shows. Round 3 ignored them and geocoded 236
cities against Nominatim at one request per second instead, for worse coverage. Before
reaching for an external source, check what the payloads already in `raw_responses` contain:
`sets.set[].name` and `song.with` were sitting there unread too.

Three things now come out of the stored payloads with no network call at all
(`ingestion/backfill.py`): coordinates, set names (1,217 song rows, 11 segments including two
full-album nights), and 12 guest credits with MusicBrainz ids.

**A validation rule cost a whole setlist.** `RawCoords` required lat and long, and one show
ships `"coords": {}`. That made the entire setlist fail validation, losing its set names and
guest credits as well. Optional fields plus an explicit "empty coords means no coords" check
in `normalize`. Be careful making a nested field mandatory: it fails the whole parent.

**Write the verifier before trusting the classifier.** `derived/notes.py` flags 536 free-text
notes by regex. The debut pattern matched "first time played since 2015", which is the
opposite of a debut, and `verify_debuts` caught it by checking every claim against the
performance history: 17 returns had been scored as debuts. After the fix, 70 claims, 60
confirmed, 10 genuinely contradicted. Those 10 stay contradicted and visible; the archive
thins out before 2010 and a missing show looks exactly like a wrong note.

Every flag stores the phrase that triggered it. That is what made the bug findable in one
query rather than by reading 536 notes.

**AcousticBrainz is indexed by recording, not by song.** Querying the single stored mbid
resolved 43 of 81 songs and missed Elephant, Let It Happen and The Less I Know the Better.
All three are analysed, under a different recording id. Searching every MusicBrainz recording
of a title took performance coverage from 45% to 88%. Coverage is reported both by song (52%)
and by performance (88%) because they differ by a lot and only quoting the flattering one
would misdescribe the data. Upstream froze in 2022, so Deadbeat will never be covered.

`mbid_client.py` had a User-Agent with no contact, the same defect already fixed for
Wikidata. MusicBrainz asks for one and throttles without it. Fixed.

**Another schema.sql gap of the same family as Round 3's.** Every `songs` enrichment column
existed only as an `ALTER TABLE` migration, so a fresh database lacked them and the new tests
failed on `no such column: mbid`. All of them, plus the venue profile columns, are now
declared in `schema.sql` with the migrations kept for existing databases. New column, both
places, every time.

**Weather is on the page as a negative result.** Open-Meteo's archive is free and covers
1940 onward, and `venue_profile.py` types 126 venues of which 41 are outdoors. On the outdoor
shows measured, rain makes no difference to setlist length, on a sample far too small to
conclude anything. The page says exactly that rather than dropping the section or dressing
the noise up as a finding.
