import { lazy, type ComponentType, type LazyExoticComponent } from "react";
import type { Icon } from "@phosphor-icons/react";
import {
  ArrowCounterClockwise,
  Atom,
  CalendarBlank,
  ChartLineUp,
  ChartScatter,
  Cpu,
  FlowArrow,
  GlobeHemisphereWest,
  GridFour,
  ListNumbers,
  MagnifyingGlass,
  MapPin,
  MicrophoneStage,
  MusicNotes,
  Notebook,
  Playlist,
  Quotes,
  Repeat,
  Timer,
  Van,
  Waveform,
} from "@phosphor-icons/react";
import type { Accent } from "../lib/theme";
import { PHOTOS, type PhotoKey } from "../lib/photos";

export type SideKey = "predictions" | "analysis";

export interface Side {
  key: SideKey;
  /** Record-sleeve name for the half of the product: the first thing the nav shows. */
  sleeve: string;
  label: string;
  accent: Accent;
  pitch: string;
}

export interface RouteDef {
  side: SideKey;
  slug: string;
  title: string;
  /** One line, shown in the tracklist tooltip, the command palette and the landing sides. */
  blurb: string;
  icon: Icon;
  Component: LazyExoticComponent<ComponentType>;
  /** Vinyl-style track code, A1..A8 and B1..B13, derived from the order below. */
  code: string;
  /** Photo revealed under the cursor when this track is hovered in a tracklist. */
  photo: PhotoKey;
}

export const SIDES: Record<SideKey, Side> = {
  predictions: {
    key: "predictions",
    sleeve: "Side A",
    label: "Predictions",
    accent: "violet",
    pitch: "What the next show is likely to hold, with the uncertainty left in.",
  },
  analysis: {
    key: "analysis",
    sleeve: "Side B",
    label: "Analysis",
    accent: "ember",
    pitch: "Eighteen years of the record itself: rooms, songs, tours and nights.",
  },
};

type Draft = Omit<RouteDef, "code" | "photo">;

const p = (slug: string, title: string, blurb: string, icon: Icon, load: () => Promise<{ default: ComponentType }>): Draft => ({
  side: "predictions",
  slug,
  title,
  blurb,
  icon,
  Component: lazy(load),
});

const a = (slug: string, title: string, blurb: string, icon: Icon, load: () => Promise<{ default: ComponentType }>): Draft => ({
  side: "analysis",
  slug,
  title,
  blurb,
  icon,
  Component: lazy(load),
});

const DRAFTS: Draft[] = [
  p("next-setlist", "Next Setlist", "Each song's chance of being played at the next show", Playlist, () => import("../pages/predictions/NextSetlist")),
  p("running-order", "Running Order", "The night decoded song by song, from the opener on", ListNumbers, () => import("../pages/predictions/RunningOrder")),
  p("concert-length", "Concert Length", "How many songs the next night should run to", Timer, () => import("../pages/predictions/ConcertLength")),
  p("encore", "Encore", "What is most likely to close the night", Repeat, () => import("../pages/predictions/Encore")),
  p("coming-back", "Coming Back", "Songs resting now that tend to return", ArrowCounterClockwise, () => import("../pages/predictions/Comeback")),
  p("song-role", "Song Role", "Opener, closer or middle: where a song usually sits", MusicNotes, () => import("../pages/predictions/SongRole")),
  p("next-date", "Next Date", "When the next show is likely to fall", CalendarBlank, () => import("../pages/predictions/NextDate")),
  p("next-country", "Next Country", "Where the tour is likely to go next", GlobeHemisphereWest, () => import("../pages/predictions/NextCountry")),

  a("venue-map", "Venue Map", "Every room played, on one map", MapPin, () => import("../pages/analysis/VenueMap")),
  a("setlist-trend", "Setlist Trend", "How the set has shifted, era by era", ChartLineUp, () => import("../pages/analysis/SetlistTrend")),
  a("tours", "Tours", "Each tour, its length and its reach", Van, () => import("../pages/analysis/Tours")),
  a("night-notes", "Night Notes", "What the setlist notes say about each night", Notebook, () => import("../pages/analysis/NightNotes")),
  a("song-explorer", "Song Explorer", "One song's whole history on stage", MagnifyingGlass, () => import("../pages/analysis/SongExplorer")),
  a("song-map", "Song Map", "Songs placed by how they are used live", ChartScatter, () => import("../pages/analysis/SongMap")),
  a("sound-profile", "Sound Profile", "Tempo, key and energy of the live catalogue", Waveform, () => import("../pages/analysis/AudioProfile")),
  a("transitions", "Transition Graph", "Which song tends to follow which", FlowArrow, () => import("../pages/analysis/TransitionGraph")),
  a("clusters", "Cluster Explorer", "Families of setlists that look alike", Atom, () => import("../pages/analysis/ClusterExplorer")),
  a("heatmaps", "Heatmaps", "Plays by song and year at a glance", GridFour, () => import("../pages/analysis/Heatmaps")),
  a("covers-encores", "Covers & Encores", "Other people's songs and the closing slots", MicrophoneStage, () => import("../pages/analysis/CoversEncores")),
  a("anecdotes", "Anecdotes", "The odd nights the numbers turned up", Quotes, () => import("../pages/analysis/Anecdotes")),
  a("models", "Models", "How every model was chosen and how it scores", Cpu, () => import("../pages/analysis/Models")),
];

// Photos cycle through the archive so neighbouring tracks never reveal the same picture.
const PHOTO_CYCLE: PhotoKey[] = [
  "guitaristConfetti",
  "silhouetteLasers",
  "singerBlur",
  "stageRainbowLights",
  "arenaAerial",
  "synthTable",
  "roundStageAerial",
  "singerConfetti",
  "arenaLasersWide",
  "backyardPortrait",
  "guitaristClose",
  "roundStageOverhead",
  "artistRedSeats",
];

export const ROUTES: RouteDef[] = DRAFTS.map((d, i) => {
  const n = DRAFTS.filter((x, j) => x.side === d.side && j <= i).length;
  return { ...d, code: `${d.side === "predictions" ? "A" : "B"}${n}`, photo: PHOTO_CYCLE[i % PHOTO_CYCLE.length] };
});

export const photoOf = (r: RouteDef) => PHOTOS[r.photo];

export const routesOf = (side: SideKey) => ROUTES.filter((r) => r.side === side);

export const findRoute = (side: string | undefined, slug: string | undefined) =>
  ROUTES.find((r) => r.side === side && r.slug === slug);

export const pathOf = (r: Pick<RouteDef, "side" | "slug">) => `/${r.side}/${r.slug}`;
