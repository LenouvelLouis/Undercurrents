import countryIso2Table from "../assets/geo/country-iso2.json";

// [name, ISO 3166-1 alpha-2 country code, longitude, latitude, population]: trimmed from
// GeoNames-derived public data (every populated place with 2000+ residents worldwide).
// Real published place coordinates, never invented ones: a venue lands on the real city it
// was reported in, not on a guessed or randomized point.
type CityRow = [string, string, number, number, number];

// The city table is ~3.3MB, far too large to inline into the JS bundle Vite ships on first
// load. It lives under public/geo/ instead, served as its own static asset and fetched lazily
// here at runtime (once, cached), so the initial bundle stays small and this data loads in the
// background while the rest of the app is already interactive.
export interface CityDataBundle {
  index: Map<string, CityRow>;
  byCountry: Map<string, CityRow[]>;
}

function stripAccents(s: string): string {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function normalize(s: string): string {
  return stripAccents(s.trim().toLowerCase()).replace(/[^a-z0-9]+/g, " ").trim();
}

const ISO2_TABLE = countryIso2Table as Record<string, string>;

/** Resolve free-text venue.country to an ISO 3166-1 alpha-2 code, for matching against
 *  the city dataset (which is keyed by the same standard). */
export function toIso2(raw: string | null | undefined): string | null {
  if (!raw) return null;
  return ISO2_TABLE[raw.trim().toLowerCase()] ?? null;
}

let cityDataPromise: Promise<CityDataBundle> | null = null;

/** Fetches and indexes the city reference table, once, caching the in-flight/resolved
 *  promise so repeated calls (e.g. from multiple components) share a single request and a
 *  single set of indices. Index cities by "iso2|normalized name" for O(1) exact lookups;
 *  ties (rare: a handful of same-named towns in one country) resolve to whichever has the
 *  larger population, since that's the one most likely to host an actual touring venue. */
export function loadCityData(): Promise<CityDataBundle> {
  if (!cityDataPromise) {
    cityDataPromise = fetch("/geo/cities.json")
      .then((res) => res.json())
      .then((rows: CityRow[]) => {
        const index = new Map<string, CityRow>();
        const byCountry = new Map<string, CityRow[]>();
        for (const row of rows) {
          const [name, iso2] = row;
          const key = `${iso2}|${normalize(name)}`;
          const existing = index.get(key);
          if (!existing || row[4] > existing[4]) index.set(key, row);
          let list = byCountry.get(iso2);
          if (!list) {
            list = [];
            byCountry.set(iso2, list);
          }
          list.push(row);
        }
        return { index, byCountry };
      });
  }
  return cityDataPromise;
}

/** Real coordinates for a venue's reported city, resolved from published place data:
 *  exact name match first, then a same-country substring match as a looser fallback
 *  (handles things like "Saint-Père" vs. the dataset's "Saint-Père-en-Retz"). Returns
 *  null (never a guess) when nothing in the dataset plausibly matches, or when the
 *  dataset hasn't finished loading yet (pass the bundle from loadCityData() once ready). */
export function cityCoordinates(
  data: CityDataBundle | null,
  city: string | null | undefined,
  country: string | null | undefined,
): [number, number] | null {
  if (!data || !city) return null;
  const iso2 = toIso2(country);
  if (!iso2) return null;
  const key = `${iso2}|${normalize(city)}`;
  const exact = data.index.get(key);
  if (exact) return [exact[2], exact[3]];

  const needle = normalize(city);
  if (needle.length < 3) return null;
  const candidates = data.byCountry.get(iso2);
  if (!candidates) return null;
  let best: CityRow | null = null;
  for (const row of candidates) {
    const name = normalize(row[0]);
    if (name.includes(needle) || needle.includes(name)) {
      if (!best || row[4] > best[4]) best = row;
    }
  }
  return best ? [best[2], best[3]] : null;
}
