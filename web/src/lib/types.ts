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
