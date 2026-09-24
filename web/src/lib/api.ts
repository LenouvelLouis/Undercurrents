// The archive does not change while someone browses it, so every GET is kept in memory for
// the visit: going back to a page is instant, and two components asking for the same data
// share one request. Failed requests are dropped from the cache so they can be retried.
const cache = new Map<string, Promise<unknown>>();

// The hosted site has no Python server: `npm run build:static` sets VITE_STATIC_API and every
// request is read from the JSON files `undercurrents.export_static` writes to public/data.
const STATIC = import.meta.env.VITE_STATIC_API === "1";
const url = (path: string) => (STATIC ? `/data${path}.json` : `/api${path}`);

function get<T>(path: string): Promise<T> {
  const hit = cache.get(path);
  if (hit) return hit as Promise<T>;
  const request = fetch(url(path)).then((response) => {
    if (!response.ok) throw new Error(`GET ${path} failed: ${response.status}`);
    return response.json() as Promise<T>;
  });
  cache.set(path, request);
  request.catch(() => cache.delete(path));
  return request;
}

import type {
  Anecdote,
  AudioFeatures,
  BacktestBundle,
  Benchmarks,
  DebutCheck,
  NightNotes,
  WeatherReport,
  ComebackPrediction,
  EncorePrediction,
  RunningOrder,
  CalendarHeatmap,
  CooccurrenceHeatmap,
  SetlistFeatureSummary,
  SongFeature,
  SongPositionHeatmap,
  SongsByYearHeatmap,
  City,
  CoverArtist,
  Encores,
  SetlistDuration,
  SongMapPoint,
  TourSummary,
  ClusterDetail,
  ClusterSummary,
  CountryPrediction,
  NextDate,
  Overview,
  SetlistLength,
  SetlistTrend,
  Eras,
  ModelHealth,
  Popularity,
  ShowDetail,
  ShowFormats,
  ShowTypePrediction,
  ShowSummary,
  Song,
  SongPrediction,
  SongRole,
  Transitions,
  Venue,
  VenueDetail,
} from "./types";

export const api = {
  shows: () => get<ShowSummary[]>("/shows"),
  eras: () => get<Eras>("/analysis/eras"),
  modelHealth: () => get<ModelHealth>("/predictions/model-health"),
  popularity: () => get<Popularity>("/analysis/popularity"),
  venue: (id: string) => get<VenueDetail>(`/analysis/venues/${id}`),
  showType: () => get<ShowTypePrediction>("/predictions/show-type"),
  showFormats: () => get<ShowFormats>("/analysis/show-formats"),
  show: (id: string) => get<ShowDetail>(`/shows/${id}`),
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
  tours: () => get<TourSummary[]>("/analysis/tours"),
  covers: () => get<CoverArtist[]>("/analysis/covers"),
  encores: () => get<Encores>("/analysis/encores"),
  songMap: () => get<SongMapPoint[]>("/analysis/song-map"),
  cities: () => get<City[]>("/analysis/cities"),
  setlistDuration: () => get<SetlistDuration>("/predictions/setlist-duration"),
  songFeatures: () => get<SongFeature[]>("/analysis/song-features"),
  setlistFeatureSummary: () => get<SetlistFeatureSummary>("/analysis/setlist-features/summary"),
  heatmapSongsByYear: () => get<SongsByYearHeatmap>("/analysis/heatmap/songs-by-year"),
  heatmapCalendar: () => get<CalendarHeatmap>("/analysis/heatmap/calendar"),
  heatmapSongPositions: () => get<SongPositionHeatmap>("/analysis/heatmap/song-positions"),
  heatmapCooccurrence: () => get<CooccurrenceHeatmap>("/analysis/heatmap/cooccurrence"),
  benchmarks: () => get<Benchmarks>("/predictions/benchmarks"),
  backtests: () => get<BacktestBundle>("/predictions/backtests"),
  nightNotes: () => get<NightNotes>("/analysis/night-notes"),
  debutCheck: () => get<DebutCheck>("/analysis/night-notes/debut-check"),
  audioFeatures: () => get<AudioFeatures>("/analysis/audio"),
  weather: () => get<WeatherReport>("/analysis/weather"),
  runningOrder: () => get<RunningOrder>("/predictions/running-order"),
  encorePrediction: () => get<EncorePrediction>("/predictions/encore"),
  comebackPrediction: () => get<ComebackPrediction>("/predictions/comeback"),
};
