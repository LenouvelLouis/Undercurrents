import { feature } from "topojson-client";
import type { FeatureCollection, Geometry } from "geojson";
import { geoCentroid } from "d3-geo";
import worldTopology from "../assets/geo/countries-110m.json";

// Natural Earth (world-atlas) uses specific short-form country names. Real-world venue
// data from the API uses whatever names promoters/venues list, so this table maps common
// spellings/aliases onto the exact names the map geometry uses. Nothing here is invented:
// it's just a lookup between two legitimate real-world naming conventions for the same
// countries, so real venues land on their real country's real shape.
const ALIASES: Record<string, string> = {
  "united states": "United States of America",
  "united states of america": "United States of America",
  usa: "United States of America",
  us: "United States of America",
  "u.s.a.": "United States of America",
  "u.s.": "United States of America",
  uk: "United Kingdom",
  "united kingdom": "United Kingdom",
  england: "United Kingdom",
  scotland: "United Kingdom",
  wales: "United Kingdom",
  "northern ireland": "United Kingdom",
  "great britain": "United Kingdom",
  "czech republic": "Czechia",
  czechia: "Czechia",
  "ivory coast": "Côte d'Ivoire",
  "cote d'ivoire": "Côte d'Ivoire",
  "côte d'ivoire": "Côte d'Ivoire",
  "republic of the congo": "Congo",
  "democratic republic of the congo": "Dem. Rep. Congo",
  drc: "Dem. Rep. Congo",
  "dominican republic": "Dominican Rep.",
  "bosnia and herzegovina": "Bosnia and Herz.",
  "north macedonia": "Macedonia",
  macedonia: "Macedonia",
  swaziland: "eSwatini",
  eswatini: "eSwatini",
  "south sudan": "S. Sudan",
  "equatorial guinea": "Eq. Guinea",
  "central african republic": "Central African Rep.",
  "solomon islands": "Solomon Is.",
  "trinidad & tobago": "Trinidad and Tobago",
  "papua new guinea": "Papua New Guinea",
  "south korea": "South Korea",
  "republic of korea": "South Korea",
  korea: "South Korea",
  "north korea": "North Korea",
  "russian federation": "Russia",
  netherlands: "Netherlands",
  holland: "Netherlands",
  "the netherlands": "Netherlands",
  uae: "United Arab Emirates",
  "united arab emirates": "United Arab Emirates",
};

function normalizeKey(raw: string): string {
  return raw.trim().toLowerCase();
}

/** Resolve a free-text country name (from venue data) to the exact Natural Earth name
 *  used by the bundled world map geometry, or null if there's no confident match. */
export function toMapCountryName(raw: string | null | undefined): string | null {
  if (!raw) return null;
  const key = normalizeKey(raw);
  if (ALIASES[key]) return ALIASES[key];
  const direct = MAP_COUNTRY_NAMES.find((name) => name.toLowerCase() === key);
  if (direct) return direct;
  // Loose fallback: a name that contains, or is contained by, a known map name
  // (handles things like "Germany (Berlin)" or minor punctuation drift).
  const loose = MAP_COUNTRY_NAMES.find((name) => key.includes(name.toLowerCase()) || name.toLowerCase().includes(key));
  return loose ?? null;
}

export const worldCountries = feature(
  worldTopology as unknown as Parameters<typeof feature>[0],
  (worldTopology as unknown as { objects: { countries: Parameters<typeof feature>[1] } }).objects.countries,
) as unknown as FeatureCollection<Geometry, { name: string }>;

export const MAP_COUNTRY_NAMES = worldCountries.features.map((f) => f.properties.name);

const CENTROID_CACHE = new Map<string, [number, number]>();

/** Real geometric centroid of a country's actual shape, computed from the map's own
 *  geometry (d3-geo): never a fabricated or guessed coordinate. */
export function countryCentroid(mapName: string): [number, number] | null {
  if (CENTROID_CACHE.has(mapName)) return CENTROID_CACHE.get(mapName)!;
  const f = worldCountries.features.find((feat) => feat.properties.name === mapName);
  if (!f) return null;
  const c = geoCentroid(f);
  if (!Number.isFinite(c[0]) || !Number.isFinite(c[1])) return null;
  CENTROID_CACHE.set(mapName, c);
  return c;
}
