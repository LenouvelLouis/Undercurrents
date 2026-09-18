export interface Overview {
  concerts_logged: number;
  years_start: number;
  years_end: number;
  venues_mapped: number;
  countries: number;
  setlist_clusters: number;
  setlist_accuracy: number | null;
  length_mae_songs: number | null;
}

export interface SongPrediction {
  song_id: number;
  song_name: string;
  probability: number;
}

export interface SetlistLength {
  predicted_songs: number;
}

export interface SongRole {
  song_id: number;
  song_name: string;
  probabilities: { opener: number; mid: number; closer: number; encore: number };
}

export interface NextDate {
  predicted_date: string;
  days_from_today: number;
  mae_days: number;
  median_absolute_error_days: number;
}

export interface CountryPrediction {
  country: string;
  probability: number;
}

export interface Song {
  id: number;
  name: string;
}

export interface Venue {
  id: string;
  name: string;
  city: string | null;
  country: string | null;
  show_count: number;
  capacity: number | null;
  last_visited: string | null;
}

export interface SetlistTrend {
  by_year: Record<string, number>;
  eras: { name: string; start_year: number; end_year: number }[];
}

export interface ClusterSummary {
  cluster_id: number;
  size: number;
  date_start: string;
  date_end: string;
  dominant_period: string;
}

export interface ClusterDetail extends ClusterSummary {
  typical_songs: { song_id: number; song_name: string }[];
}

export interface Transitions {
  song_id: number;
  song_name: string;
  follow_ons: { song_id: number; song_name: string; probability: number }[];
}

export interface Anecdote {
  date: string;
  tag: string;
  description: string;
}

export interface TourSummary {
  tour_id: number;
  name: string;
  year_start: number;
  year_end: number;
  show_count: number;
  date_start: string | null;
  date_end: string | null;
  venue_count: number;
  country_count: number;
  avg_songs: number | null;
  travel_km?: number | null;
  longest_hop_km?: number | null;
  legs_known?: number;
  legs_total?: number;
}

export interface CoverArtist {
  artist_id: string;
  artist_name: string;
  play_count: number;
  song_count: number;
  first_played: string;
  last_played: string;
  songs: { song_name: string; play_count: number }[];
}

export interface Encores {
  shows_with_encore: number;
  shows_total: number;
  encore_entries: number;
  encore_rate: number | null;
  songs: { song_id: number; song_name: string; encore_count: number }[];
}

export interface SongMapPoint {
  song_id: number;
  song_name: string;
  x: number;
  y: number;
  cluster_id: number;
  play_count: number;
}

export interface City {
  city: string;
  country: string | null;
  show_count: number;
  venue_count: number;
  last_visited: string | null;
}

export interface SetlistDuration {
  predicted_minutes: number;
  predicted_songs: number;
  mean_song_minutes: number;
  duration_basis: string;
  method: string;
  measured_mean_minutes: number | null;
  measured_median_minutes: number | null;
  measured_shows: number;
  shows_total: number;
  duration_coverage: number | null;
}

export interface SongFeature {
  song_id: number;
  song_name: string;
  play_count: number;
  show_count: number;
  first_played: string | null;
  last_played: string | null;
  longest_gap_days: number | null;
  current_streak: number;
  opener_count: number;
  closer_count: number;
  encore_count: number;
  cover_count: number;
  avg_position_pct: number | null;
  dominant_era: string | null;
}

export interface SetlistFeatureSummary {
  shows: number;
  avg_songs?: number | null;
  avg_encores?: number | null;
  avg_novelty?: number | null;
  avg_gap_days?: number | null;
  avg_travel_km?: number | null;
  total_travel_km?: number | null;
  legs_known?: number;
  covers?: number;
  shows_fully_timed?: number;
  by_year?: { year: number; avg_novelty: number; avg_songs: number; shows: number }[];
}

export interface SongsByYearHeatmap {
  songs: { song_id: number; song_name: string; plays: number }[];
  years: number[];
  cells: { song_id: number; year: number; plays: number }[];
}

export interface CalendarHeatmap {
  years: number[];
  cells: { year: number; month: number; shows: number }[];
}

export interface SongPositionHeatmap {
  buckets: number;
  songs: { song_id: number; song_name: string; plays: number }[];
  cells: { song_id: number; bucket: number; plays: number }[];
}

export interface CooccurrenceHeatmap {
  songs: { song_id: number; song_name: string; shows: number }[];
  pairs: { a_id: number; b_id: number; shows: number }[];
}

interface BenchmarkScores {
  name: string;
  top_1_accuracy?: number;
  top_5_accuracy?: number;
  predictions?: number;
  accuracy?: number;
  precision?: number;
  recall?: number;
  f1?: number;
}

export interface Benchmarks {
  generated_at: string;
  holdout_shows: number;
  total_shows: number;
  split_note: string;
  sequence: {
    task: string;
    vocabulary: number;
    train_shows: number;
    test_shows: number;
    baseline: BenchmarkScores;
    model: BenchmarkScores;
    top_1_delta: number;
    winner: string;
  };
  item2vec: {
    task: string;
    dimensions: number;
    songs: number;
    train_shows: number;
    note: string;
    neighbours: {
      song_id: number;
      song_name: string;
      neighbours: { song_id: number; song_name: string; similarity: number }[];
    }[];
  };
  tabular?: {
    task?: string;
    features?: string[];
    train_rows?: number;
    test_rows?: number;
    baseline?: BenchmarkScores;
    model?: BenchmarkScores;
    f1_delta?: number;
    winner?: string;
    error?: string;
  };
}

export interface RunningOrderEntry {
  position: number;
  song_id: number;
  song_name: string;
  confidence: number;
}

export interface RunningOrderRun {
  seed_length: number;
  shows_scored: number;
  songs_scored: number;
  model: { songs_included: number; exact_position: number };
  baselines: {
    markov: { name: string; songs_included: number; exact_position: number };
    most_played: { name: string; songs_included: number; exact_position: number };
  };
  songs_included_delta: number;
  winner: string;
}

export interface RunningOrderProduction {
  seed: string;
  shows_scored: number;
  songs_scored: number;
  opener_repeat_rate: number;
  model: { songs_included: number; exact_position: number };
  baseline: { name: string; songs_included: number; exact_position: number };
  songs_included_delta: number;
  winner: string;
}

export interface RunningOrderAccuracy {
  task: string;
  train_shows: number;
  test_shows: number;
  runs: RunningOrderRun[];
  model_beats_baselines_from_seed: number | null;
  production: RunningOrderProduction;
}

export interface RunningOrder {
  length: number;
  length_source: string;
  seed_length: number;
  seed_source: string;
  seed: RunningOrderEntry[];
  order: RunningOrderEntry[];
  trained_on_shows: number;
  accuracy: RunningOrderAccuracy;
}

export interface MethodScore {
  key: string;
  name: string;
  validation_precision: number;
  fold_precisions: number[];
  test_precision: number;
  chosen: boolean;
}

export interface SelectionRationale {
  leader: string;
  leader_mean: number;
  chosen_mean: number;
  reason: string;
}

export interface EncoreAccuracy {
  task: string;
  chosen_method: string;
  selection: SelectionRationale;
  train_rows: number;
  test_shows: number;
  encore_slots: number;
  validation_folds: number;
  validation_shows: number;
  precision: number;
  methods: MethodScore[];
  margin_over_next_best: number;
}

export interface EncoreCandidate {
  song_id: number;
  song_name: string;
  probability: number;
  recent_encore_rate: number;
  encore_count: number;
  play_count: number;
}

export interface EncorePrediction {
  method: string;
  method_name: string;
  candidates: EncoreCandidate[];
  accuracy: EncoreAccuracy;
}

export interface ComebackAccuracy {
  task: string;
  chosen_method: string;
  selection: SelectionRationale;
  train_rows: number;
  test_shows: number;
  return_slots: number;
  validation_folds: number;
  validation_shows: number;
  candidate_return_rate: number;
  precision: number;
  methods: MethodScore[];
  margin_over_next_best: number;
}

export interface ComebackCandidate {
  song_id: number;
  song_name: string;
  probability: number;
  shows_since_last_play: number;
  days_since_last_play: number;
  overdue_ratio: number;
  recent_play_rate: number;
  play_count: number;
}

export interface ComebackPrediction {
  method: string;
  method_name: string;
  candidates: ComebackCandidate[];
  accuracy: ComebackAccuracy;
}

export interface BacktestBundle {
  backtests: {
    running_order?: RunningOrderAccuracy;
    encore?: EncoreAccuracy;
    comeback?: ComebackAccuracy;
  };
  missing: string[];
  command: string;
}
