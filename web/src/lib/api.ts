async function get<T>(path: string): Promise<T> {
  const response = await fetch(`/api${path}`);
  if (!response.ok) {
    throw new Error(`GET ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

import type {
  Anecdote,
  ClusterDetail,
  ClusterSummary,
  CountryPrediction,
  NextDate,
  Overview,
  SetlistLength,
  SetlistTrend,
  Song,
  SongPrediction,
  SongRole,
  Transitions,
  Venue,
} from "./types";

export const api = {
  overview: () => get<Overview>("/stats/overview"),
  songs: () => get<Song[]>("/songs"),
  nextSetlist: () => get<SongPrediction[]>("/predictions/next-setlist"),
  setlistLength: () => get<SetlistLength>("/predictions/setlist-length"),
  songRole: (songId: number) => get<SongRole>(`/predictions/song-role/${songId}`),
  nextDate: () => get<NextDate>("/predictions/next-date"),
  nextCountry: () => get<CountryPrediction[]>("/predictions/next-country"),
  venues: () => get<Venue[]>("/analysis/venues"),
  setlistTrend: () => get<SetlistTrend>("/analysis/setlist-trend"),
  clusters: () => get<ClusterSummary[]>("/analysis/clusters"),
  clusterDetail: (clusterId: number) => get<ClusterDetail>(`/analysis/clusters/${clusterId}`),
  transitions: (songId: number) => get<Transitions>(`/analysis/transitions/${songId}`),
  anecdotes: () => get<Anecdote[]>("/analysis/anecdotes"),
};
