import { useEffect, useMemo, useState } from "react";
import { ComposableMap, Geographies, Geography, Marker, ZoomableGroup } from "react-simple-maps";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import { countryCentroid, toMapCountryName, worldCountries } from "../../lib/countryGeo";
import { cityCoordinates, loadCityData, type CityDataBundle } from "../../lib/cityGeo";
import { api } from "../../lib/api";
import PhotoPanel from "../../components/PhotoPanel";
import { PHOTOS } from "../../lib/photos";
import type { City, Venue } from "../../lib/types";

interface CountryAgg {
  mapName: string;
  label: string;
  venues: Venue[];
  totalShows: number;
  coordinates: [number, number];
}

interface PointGroup {
  key: string;
  coordinates: [number, number];
  venues: Venue[];
  totalShows: number;
  precision: "city" | "country";
}

type Selection = { kind: "country"; name: string } | { kind: "point"; key: string } | null;

const DEFAULT_VIEW = { coordinates: [10, 20] as [number, number], zoom: 1 };
const MAP_MIN_ZOOM = 1;
const MAP_MAX_ZOOM = 48;

export default function VenueMap() {
  const [venues, setVenues] = useState<Venue[]>([]);
  const [selected, setSelected] = useState<Selection>(null);
  const [hoveredCountry, setHoveredCountry] = useState<string | null>(null);
  const [zoom, setZoom] = useState(DEFAULT_VIEW);
  const [cityData, setCityData] = useState<CityDataBundle | null>(null);
  const [cities, setCities] = useState<City[]>([]);

  useEffect(() => {
    api.venues().then(setVenues).catch(() => {});
    api.cities().then(setCities).catch(() => {});
  }, []);

  // The per-venue city coordinate table is fetched lazily (see cityGeo.ts) rather than
  // bundled, so it loads in the background here; until it resolves, points fall back to
  // their real country centroid and quietly sharpen to city-level once the data arrives.
  useEffect(() => {
    loadCityData()
      .then(setCityData)
      .catch(() => {});
  }, []);

  // Country-level wash behind the pins, so the map still reads at a glance even before
  // zooming in on individual points. Real country geometry, aggregated from real venues.
  const byCountry = useMemo(() => {
    const map = new Map<string, CountryAgg>();
    for (const venue of venues) {
      const mapName = toMapCountryName(venue.country);
      if (!mapName) continue;
      const centroid = countryCentroid(mapName);
      if (!centroid) continue;
      const existing = map.get(mapName);
      if (existing) {
        existing.venues.push(venue);
        existing.totalShows += venue.show_count;
      } else {
        map.set(mapName, { mapName, label: venue.country ?? mapName, venues: [venue], totalShows: venue.show_count, coordinates: centroid });
      }
    }
    return map;
  }, [venues]);

  // One point per venue wherever we can place it on its real, published city (falling
  // back to the country's real centroid only when the city isn't in the reference data).
  // Venues that land on the exact same real coordinate (genuinely the same town, or the
  // same country-level fallback) share one clickable point rather than stacking hidden
  // duplicates.
  const points = useMemo(() => {
    const map = new Map<string, PointGroup>();
    let unresolved = 0;
    let cityMatched = 0;
    for (const venue of venues) {
      const mapName = toMapCountryName(venue.country);
      const city = cityCoordinates(cityData, venue.city, venue.country);
      const country = mapName ? countryCentroid(mapName) : null;
      const coords = city ?? country;
      if (!coords) {
        unresolved++;
        continue;
      }
      if (city) cityMatched++;
      const precision: "city" | "country" = city ? "city" : "country";
      const key = `${coords[0].toFixed(2)},${coords[1].toFixed(2)}`;
      const existing = map.get(key);
      if (existing) {
        existing.venues.push(venue);
        existing.totalShows += venue.show_count;
        if (precision === "city") existing.precision = "city";
      } else {
        map.set(key, { key, coordinates: coords, venues: [venue], totalShows: venue.show_count, precision });
      }
    }
    return { groups: Array.from(map.values()), unresolved, cityMatched };
  }, [venues, cityData]);

  const maxShows = Math.max(...points.groups.map((c) => c.totalShows), 1);
  const activeCountry = selected?.kind === "country" ? byCountry.get(selected.name) : null;
  const activePoint = selected?.kind === "point" ? points.groups.find((p) => p.key === selected.key) : null;
  const cityResolved = points.cityMatched;

  // Two real leaderboards beside the map: the most played venues, carved out of the venue
  // list already on the page, and the most played cities, which come from their own
  // endpoint. Venue capacity used to fill the second panel, but that column is empty for
  // every venue in the database, so the panel was permanently blank.
  const byShows = useMemo(() => venues.slice().sort((a, b) => b.show_count - a.show_count).slice(0, 8), [venues]);
  const topCities = useMemo(() => cities.slice(0, 8), [cities]);
  const maxCityShows = Math.max(...topCities.map((c) => c.show_count), 1);
  const withCapacity = useMemo(() => venues.filter((v) => v.capacity != null), [venues]);
  const byCapacity = useMemo(
    () => withCapacity.slice().sort((a, b) => (b.capacity ?? 0) - (a.capacity ?? 0)).slice(0, 8),
    [withCapacity],
  );
  const maxCapacity = Math.max(...byCapacity.map((v) => v.capacity ?? 0), 1);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.arenaAerial.src} alt={PHOTOS.arenaAerial.alt} size={56} accent="ember" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">
            Venue Map
          </h1>
        </div>
        <p className="max-w-sm text-sm leading-relaxed text-white/50 sm:text-right">
          {venues.length} venues, {points.groups.length} points on the map (click one for details)
          <br />
          scroll, drag, or use the + / − to explore
        </p>
      </div>

      <div className="mt-10 grid grid-cols-5 gap-6">
        <Card className="anim-fade-in-up relative col-span-5 overflow-hidden p-0 lg:col-span-3" tinted accent="ember">
          <div className="pointer-events-none absolute -left-10 -top-10 h-56 w-56 rounded-full bg-ember/20 blur-3xl" />
          <div className="absolute right-3 top-3 z-10 flex flex-col overflow-hidden rounded-lg border border-white/15 bg-ink/80 backdrop-blur-sm">
            <button
              type="button"
              onClick={() => setZoom((z) => ({ ...z, zoom: Math.min(MAP_MAX_ZOOM, +(z.zoom * 1.6).toFixed(2)) }))}
              disabled={zoom.zoom >= MAP_MAX_ZOOM}
              className="flex h-7 w-7 items-center justify-center font-mono text-sm text-white/70 transition-colors hover:bg-white/10 hover:text-white disabled:opacity-30"
              aria-label="Zoom in"
            >
              +
            </button>
            <div className="h-px bg-white/10" />
            <button
              type="button"
              onClick={() => setZoom((z) => ({ ...z, zoom: Math.max(MAP_MIN_ZOOM, +(z.zoom / 1.6).toFixed(2)) }))}
              disabled={zoom.zoom <= MAP_MIN_ZOOM}
              className="flex h-7 w-7 items-center justify-center font-mono text-sm text-white/70 transition-colors hover:bg-white/10 hover:text-white disabled:opacity-30"
              aria-label="Zoom out"
            >
              −
            </button>
            <div className="h-px bg-white/10" />
            <button
              type="button"
              onClick={() => setZoom(DEFAULT_VIEW)}
              className="flex h-7 w-7 items-center justify-center text-[11px] text-white/70 transition-colors hover:bg-white/10 hover:text-white"
              aria-label="Reset view"
              title="Reset view"
            >
              ⟲
            </button>
          </div>
          <div className="pointer-events-none relative z-10 flex flex-wrap items-center gap-x-4 gap-y-1 px-4 pt-4 pr-28">
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: "#e2492f" }} />
              <span className="text-[13px] font-medium text-white/55">exact city</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full" style={{ backgroundColor: "#a5462f" }} />
              <span className="text-[13px] font-medium text-white/55">country center, city unresolved</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full border border-white/50" />
              <span className="text-[13px] font-medium text-white/55">size = shows played</span>
            </div>
          </div>
          <ComposableMap projection="geoNaturalEarth1" projectionConfig={{ scale: 148 }} className="h-[560px] w-full">
            <ZoomableGroup
              center={zoom.coordinates}
              zoom={zoom.zoom}
              minZoom={MAP_MIN_ZOOM}
              maxZoom={MAP_MAX_ZOOM}
              onMoveEnd={(pos) => setZoom({ coordinates: pos.coordinates ?? zoom.coordinates, zoom: pos.zoom ?? zoom.zoom })}
            >
              <Geographies geography={worldCountries}>
                {({ geographies }) =>
                  geographies.map((geo) => {
                    const name = (geo.properties as { name?: string } | null)?.name;
                    if (!name) return null;
                    const agg = byCountry.get(name);
                    const isActive = selected?.kind === "country" && selected.name === name;
                    const isHovered = name === hoveredCountry;
                    const fill = !agg
                      ? "rgba(255,255,255,0.05)"
                      : isActive
                        ? "rgba(226,73,47,0.4)"
                        : isHovered
                          ? "rgba(226,73,47,0.3)"
                          : "rgba(226,73,47,0.16)";
                    const stroke = !agg
                      ? "rgba(255,255,255,0.08)"
                      : isActive || isHovered
                        ? "rgba(226,73,47,0.7)"
                        : "rgba(226,73,47,0.4)";
                    return (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        onClick={() => agg && setSelected(isActive ? null : { kind: "country", name })}
                        onMouseEnter={() => agg && setHoveredCountry(name)}
                        onMouseLeave={() => setHoveredCountry((h) => (h === name ? null : h))}
                        style={{
                          fill,
                          stroke,
                          strokeWidth: 0.5,
                          outline: "none",
                          cursor: agg ? "pointer" : "default",
                          transition: "fill 0.2s ease, stroke 0.2s ease",
                        }}
                      />
                    );
                  })
                }
              </Geographies>
              {points.groups.map((p, i) => {
                // ZoomableGroup scales everything nested inside it, markers included, so a
                // fixed radius would balloon to a screen-filling blob at high zoom if left
                // uncompensated. Counter-scale by 1/sqrt(zoom) rather than 1/zoom: that still
                // lets points visibly grow as you zoom in (so close-together venues actually
                // get easier to make out and click), just sub-linearly, instead of staying a
                // fixed size or exploding.
                const invScale = 1 / Math.sqrt(zoom.zoom);
                const r = (2.5 + (p.totalShows / maxShows) * 7) * invScale;
                const isActive = selected?.kind === "point" && selected.key === p.key;
                return (
                  // Note: the pop-in animation lives on the inner <circle>, never on this
                  // <Marker> (an SVG <g>) itself: react-simple-maps positions each marker
                  // with its own transform:translate(x,y), and a CSS `transform` animation on
                  // the same element would overwrite that translate, collapsing every marker
                  // onto a single point instead of its real map coordinates.
                  <Marker
                    key={p.key}
                    coordinates={p.coordinates}
                    onClick={() => setSelected(isActive ? null : { kind: "point", key: p.key })}
                    className="cursor-pointer"
                  >
                    {isActive && <circle r={r + 5 * invScale} fill="none" stroke="#ff9270" strokeWidth={1 * invScale} opacity={0.6} />}
                    <circle
                      r={r}
                      fill={isActive ? "#ff9270" : p.precision === "city" ? "#e2492f" : "#a5462f"}
                      fillOpacity={isActive ? 1 : 0.9}
                      stroke="#1a0b06"
                      strokeWidth={0.75 * invScale}
                      className="anim-pop-in"
                      style={{ animationDelay: `${0.05 + (i % 40) * 0.012}s` }}
                    />
                  </Marker>
                );
              })}
              {/* The active point's popup is rendered last and on its own, dedicated Marker
                  rather than nested inside the point's own <g>: SVG has no z-index, only DOM
                  order, so with dozens of points close together (a dense city like Paris) a
                  neighbor drawn later in the loop would otherwise render on top of an earlier
                  point's popup and cut through its text. Rendering it after every other point,
                  in the map's own coordinate space, keeps it pinned above the whole map (and
                  still panning/zooming with it) no matter which point is selected. */}
              {activePoint && (
                <Marker coordinates={activePoint.coordinates} style={{ pointerEvents: "none" }}>
                  {(() => {
                    const invScale = 1 / Math.sqrt(zoom.zoom);
                    const r = (2.5 + (activePoint.totalShows / maxShows) * 7) * invScale;
                    const label =
                      activePoint.venues.length === 1
                        ? activePoint.venues[0].name
                        : (activePoint.venues[0].city ?? activePoint.venues[0].name);
                    const popupW = Math.max(70, label.length * 5.6 + 20) * invScale;
                    const popupH = 34 * invScale;
                    return (
                      <g transform={`translate(0, ${-(r + popupH + 6 * invScale)})`}>
                        <rect
                          x={-popupW / 2}
                          y={0}
                          width={popupW}
                          height={popupH}
                          rx={6 * invScale}
                          fill="#1a0b06"
                          stroke="#ff9270"
                          strokeWidth={1 * invScale}
                        />
                        <text
                          x={0}
                          y={popupH * 0.42}
                          textAnchor="middle"
                          className="font-mono"
                          fontSize={10 * invScale}
                          fontWeight={700}
                          fill="white"
                        >
                          {label}
                        </text>
                        <text
                          x={0}
                          y={popupH * 0.8}
                          textAnchor="middle"
                          className="font-mono"
                          fontSize={8 * invScale}
                          fill="rgba(255,255,255,0.6)"
                        >
                          {activePoint.venues.length} venue{activePoint.venues.length === 1 ? "" : "s"} ·{" "}
                          {activePoint.totalShows} shows
                        </text>
                        <path
                          d={`M ${-5 * invScale} ${popupH} L 0 ${popupH + 5 * invScale} L ${5 * invScale} ${popupH} Z`}
                          fill="#1a0b06"
                          stroke="#ff9270"
                          strokeWidth={1 * invScale}
                        />
                      </g>
                    );
                  })()}
                </Marker>
              )}
            </ZoomableGroup>
          </ComposableMap>
          <div className="grain-overlay" />
          <div className="text-[13px] font-medium pointer-events-none absolute bottom-3 left-4 text-white/45">
            {cityResolved} of {venues.length} venues placed on their real city, rest on country center
          </div>
        </Card>

        <Card className="anim-fade-in-up col-span-5 lg:col-span-2" style={{ animationDelay: "0.1s" }}>
          {!activeCountry && !activePoint && (
            <div className="flex h-full min-h-[480px] flex-col items-center justify-center gap-3 text-center text-white/30">
              <div className="h-16 w-16 rounded-full border-2 border-dashed border-white/15" />
              <p className="font-mono text-xs">Click a point (or a country) on the map to see its venues</p>
            </div>
          )}
          {(activeCountry || activePoint) && (
            <div>
              <div className="flex items-center justify-between">
                <h2 className="font-display text-2xl font-bold">
                  {activePoint ? activePoint.venues[0].city ?? activePoint.venues[0].name : activeCountry!.label}
                </h2>
                <span className="text-[13px] font-medium rounded-full border border-ember/40 px-2 py-0.5 text-ember-light">
                  {(activePoint ?? activeCountry!).venues.length} venue{(activePoint ?? activeCountry!).venues.length === 1 ? "" : "s"}
                </span>
              </div>
              <div className="mt-1 font-mono text-xs text-white/40">
                {(activePoint ?? activeCountry!).totalShows} shows played here in total
                {activePoint?.precision === "country" && " (exact city unresolved, grouped by country)"}
              </div>
              <div className="mt-5 max-h-[440px] space-y-3 overflow-y-auto pr-1">
                {(activePoint ?? activeCountry!).venues
                  .slice()
                  .sort((a, b) => b.show_count - a.show_count)
                  .map((venue, i) => (
                    <div
                      key={venue.id}
                      className="anim-fade-in-up rounded-lg border border-white/5 bg-white/[0.02] p-3"
                      style={{ animationDelay: `${i * 0.04}s` }}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium">{venue.name}</span>
                        <span className="shrink-0 font-mono text-[10px] text-white/40">
                          {venue.show_count} show{venue.show_count === 1 ? "" : "s"}
                        </span>
                      </div>
                      <div className="mt-1 flex items-center justify-between font-mono text-[10px] text-white/40">
                        <span>{venue.city ?? "N/A"}</span>
                        <span>{venue.last_visited ?? "N/A"}</span>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="anim-fade-in-up" accent="ember">
          <div className="text-[13px] font-medium text-white/55">Most played venues</div>
          <div className="mt-4 space-y-3">
            {byShows.map((venue, i) => (
              <div key={venue.id} className="anim-fade-in-up" style={{ animationDelay: `${i * 0.04}s` }}>
                <div className="flex items-center justify-between font-mono text-xs text-white/60">
                  <span className="truncate font-display text-sm font-medium text-white">{venue.name}</span>
                  <span className="shrink-0">{venue.show_count} show{venue.show_count === 1 ? "" : "s"}</span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/5">
                  <div
                    className="anim-width-in h-full rounded-full bg-gradient-to-r from-ember-dark via-ember to-ember-light"
                    style={{ width: `${Math.max(4, (venue.show_count / maxShows) * 100)}%`, animationDelay: `${0.1 + i * 0.05}s` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="anim-fade-in-up" accent="ember" style={{ animationDelay: "0.05s" }}>
          <div className="flex items-baseline justify-between">
            <div className="text-[13px] font-medium text-white/55">Most played cities</div>
            <div className="font-mono text-[10px] text-white/30">{cities.length} cities</div>
          </div>
          <div className="mt-4 space-y-3">
            {topCities.map((city, i) => (
              <div key={`${city.city}-${city.country}`} className="anim-fade-in-up" style={{ animationDelay: `${i * 0.04}s` }}>
                <div className="flex items-center justify-between gap-3 font-mono text-xs text-white/60">
                  <span className="truncate font-display text-sm font-medium text-white">
                    {city.city}
                    {city.country ? <span className="ml-2 font-mono text-[10px] text-white/35">{city.country}</span> : null}
                  </span>
                  <span className="shrink-0">{city.show_count} shows</span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/5">
                  <div
                    className="anim-width-in h-full rounded-full bg-gradient-to-r from-ember-dark via-ember to-ember-light"
                    style={{ width: `${Math.max(4, (city.show_count / maxCityShows) * 100)}%`, animationDelay: `${0.1 + i * 0.05}s` }}
                  />
                </div>
                <div className="mt-1 font-mono text-[10px] text-white/30">
                  {city.venue_count} venue{city.venue_count === 1 ? "" : "s"}
                </div>
              </div>
            ))}
            {topCities.length === 0 && <p className="font-mono text-xs text-white/30">Loading cities…</p>}
          </div>
        </Card>

        <Card className="anim-fade-in-up" accent="ember" style={{ animationDelay: "0.1s" }}>
          <div className="flex items-baseline justify-between">
            <div className="text-[13px] font-medium text-white/55">Biggest rooms played</div>
            <div className="font-mono text-[10px] text-white/30">{withCapacity.length} known</div>
          </div>
          <div className="mt-4 space-y-3">
            {byCapacity.map((venue, i) => (
              <div key={venue.id} className="anim-fade-in-up" style={{ animationDelay: `${i * 0.04}s` }}>
                <div className="flex items-center justify-between gap-3 font-mono text-xs text-white/60">
                  <span className="truncate font-display text-sm font-medium text-white">{venue.name}</span>
                  <span className="shrink-0">{venue.capacity?.toLocaleString()}</span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-white/5">
                  <div
                    className="anim-width-in h-full rounded-full bg-gradient-to-r from-ember-dark via-ember to-ember-light"
                    style={{ width: `${Math.max(4, ((venue.capacity ?? 0) / maxCapacity) * 100)}%`, animationDelay: `${0.1 + i * 0.05}s` }}
                  />
                </div>
              </div>
            ))}
            {byCapacity.length === 0 && (
              <p className="font-mono text-xs text-white/30">No capacity resolved for these venues yet.</p>
            )}
          </div>
          <p className="mt-4 text-[13px] leading-relaxed text-white/25">
            Capacity comes from Wikidata and only resolves where a venue name maps to exactly
            one entity in its own country, so this ranks the {withCapacity.length} rooms that
            matched, not all {venues.length}.
          </p>
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-3 gap-6">
        <PhotoPanel
          photo={PHOTOS.roundStageAerial}
          accent="ember"
          tag="one of the 89"
          className="col-span-3 h-[20rem] lg:col-span-1"
          focus="center 35%"
        />
        <PhotoPanel
          photo={PHOTOS.guitaristConfetti}
          accent="ember"
          className="col-span-3 h-[20rem] lg:col-span-2"
          focus="center 50%"
          style={{ animationDelay: "0.08s" }}
        />
      </div>
    </div>
  );
}
