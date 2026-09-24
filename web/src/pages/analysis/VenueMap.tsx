import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent } from "react";
import { ArrowRight, ArrowsIn, Minus, Pause, Play, Plus, X } from "@phosphor-icons/react";
import { ComposableMap, Geographies, Geography, Line, Marker, ZoomableGroup } from "react-simple-maps";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import { countryCentroid, toMapCountryName, worldCountries } from "../../lib/countryGeo";
import { cityCoordinates, loadCityData, type CityDataBundle } from "../../lib/cityGeo";
import { api } from "../../lib/api";
import PhotoPanel from "../../components/PhotoPanel";
import { PHOTOS } from "../../lib/photos";
import type { City, ShowSummary, Venue, VenueDetail } from "../../lib/types";

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
  precision: "venue" | "city" | "country";
  years: Set<number>;
}

interface Popup {
  x: number;
  y: number;
  group?: PointGroup;
  country?: CountryAgg;
}


const DEFAULT_VIEW = { coordinates: [10, 20] as [number, number], zoom: 1 };
const MAP_MIN_ZOOM = 1;
const MAP_MAX_ZOOM = 48;

export default function VenueMap() {
  const [venues, setVenues] = useState<Venue[]>([]);
  const [hoveredCountry, setHoveredCountry] = useState<string | null>(null);
  const [zoom, setZoom] = useState(DEFAULT_VIEW);
  const [cityData, setCityData] = useState<CityDataBundle | null>(null);
  const [cities, setCities] = useState<City[]>([]);
  const [shows, setShows] = useState<ShowSummary[]>([]);

  useEffect(() => {
    api.venues().then(setVenues).catch(() => {});
    api.cities().then(setCities).catch(() => {});
    api.shows().then(setShows).catch(() => {});
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
      const exact: [number, number] | null =
        venue.latitude != null && venue.longitude != null ? [venue.longitude, venue.latitude] : null;
      const mapName = toMapCountryName(venue.country);
      const city = exact ? null : cityCoordinates(cityData, venue.city, venue.country);
      const country = mapName ? countryCentroid(mapName) : null;
      const coords = exact ?? city ?? country;
      if (!coords) {
        unresolved++;
        continue;
      }
      if (exact || city) cityMatched++;
      const precision: PointGroup["precision"] = exact ? "venue" : city ? "city" : "country";
      const key = `${coords[0].toFixed(3)},${coords[1].toFixed(3)}`;
      const existing = map.get(key);
      if (existing) {
        existing.venues.push(venue);
        existing.totalShows += venue.show_count;
        (venue.years ?? []).forEach((y) => existing.years.add(y));
      } else {
        map.set(key, { key, coordinates: coords, venues: [venue], totalShows: venue.show_count, precision, years: new Set(venue.years ?? []) });
      }
    }
    return { groups: Array.from(map.values()).sort((a, b) => a.totalShows - b.totalShows), unresolved, cityMatched };
  }, [venues, cityData]);

  // Timeline: null shows every venue; a year shows every room played up to then, and lights
  // up the ones played that year, so pressing play draws the band's map as it grew.
  const allYears = useMemo(() => {
    const ys = new Set<number>();
    venues.forEach((v) => (v.years ?? []).forEach((y) => ys.add(y)));
    return [...ys].sort((a, b) => a - b);
  }, [venues]);
  const [year, setYear] = useState<number | null>(null);
  const coordsByVenue = useMemo(() => {
    const m = new Map<string, [number, number]>();
    points.groups.forEach((g) => g.venues.forEach((v) => m.set(v.id, g.coordinates)));
    return m;
  }, [points]);
  // the year's shows in date order, as legs from one city to the next
  const route = useMemo(() => {
    if (year === null) return [];
    const stops = shows
      .filter((s) => s.event_date.startsWith(String(year)) && s.venue_id && coordsByVenue.has(s.venue_id))
      .sort((a, b) => a.event_date.localeCompare(b.event_date))
      .map((s) => coordsByVenue.get(s.venue_id!)!);
    const legs: { from: [number, number]; to: [number, number] }[] = [];
    for (let i = 1; i < stops.length; i++) {
      if (stops[i][0] !== stops[i - 1][0] || stops[i][1] !== stops[i - 1][1]) legs.push({ from: stops[i - 1], to: stops[i] });
    }
    return legs;
  }, [year, shows, coordsByVenue]);
  const yearShows = year === null ? 0 : shows.filter((s) => s.event_date.startsWith(String(year))).length;
  const [playing, setPlaying] = useState(false);
  // how long each year stays on screen while playing; the route is drawn over most of it
  const SPEEDS = { slow: 6000, normal: 3800, fast: 2000 } as const;
  const [speed, setSpeed] = useState<keyof typeof SPEEDS>("normal");
  const stepMs = SPEEDS[speed];
  const drawSeconds = playing ? (stepMs * 0.75) / 1000 : 2.4;
  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      setYear((y) => {
        const i = y === null ? -1 : allYears.indexOf(y);
        if (i + 1 >= allYears.length) {
          setPlaying(false);
          return null;
        }
        return allYears[i + 1];
      });
    }, stepMs);
    return () => window.clearInterval(id);
  }, [playing, allYears, stepMs]);

  // Popups are HTML over the map, not SVG inside it: real text, real links, and a layout that
  // does not scale with the zoom level.
  const mapRef = useRef<HTMLDivElement>(null);
  const [popup, setPopup] = useState<Popup | null>(null);
  const [hover, setHover] = useState<{ x: number; y: number; label: string; sub: string } | null>(null);
  const [detail, setDetail] = useState<VenueDetail | null>(null);
  const [detailId, setDetailId] = useState<string | null>(null);
  useEffect(() => {
    if (!detailId) return;
    setDetail(null);
    api.venue(detailId).then(setDetail).catch(() => {});
  }, [detailId]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setPopup(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const localPoint = (e: { clientX: number; clientY: number }) => {
    const box = mapRef.current?.getBoundingClientRect();
    return box ? { x: e.clientX - box.left, y: e.clientY - box.top } : { x: 0, y: 0 };
  };
  const openGroup = (e: ReactMouseEvent, group: PointGroup) => {
    const pt = localPoint(e);
    setHover(null);
    setPopup({ ...pt, group });
    setDetailId(group.venues.length === 1 ? group.venues[0].id : null);
  };

  const maxShows = Math.max(...points.groups.map((c) => c.totalShows), 1);
  const activeKey = popup?.group?.key ?? null;
  const activeCountryName = popup?.country?.mapName ?? null;
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

      <Card className="relative mt-10 overflow-hidden p-0 sm:p-0" tinted accent="ember">
        <div ref={mapRef} className="relative" onPointerLeave={() => setHover(null)}>
          {/* legend */}
          <div className="pointer-events-none absolute left-5 top-5 z-10 flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-white/55">
            <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-ember-light shadow-[0_0_10px_2px_rgba(255,146,112,0.7)]" /> city played</span>
            <span className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-[#8a4a3a]" /> placed on its country</span>
            <span>size = shows played</span>
            <span className="text-white/35">{cityResolved} of {venues.length} venues placed on their city</span>
          </div>

          {/* zoom controls */}
          <div className="absolute right-4 top-4 z-10 flex flex-col overflow-hidden rounded-xl bg-ink/70 ring-1 ring-white/10 backdrop-blur-xl">
            {[
              { label: "Zoom in", icon: Plus, onClick: () => setZoom((z) => ({ ...z, zoom: Math.min(MAP_MAX_ZOOM, +(z.zoom * 1.6).toFixed(2)) })) },
              { label: "Zoom out", icon: Minus, onClick: () => setZoom((z) => ({ ...z, zoom: Math.max(MAP_MIN_ZOOM, +(z.zoom / 1.6).toFixed(2)) })) },
              { label: "Reset view", icon: ArrowsIn, onClick: () => { setZoom(DEFAULT_VIEW); setPopup(null); } },
            ].map(({ label, icon: Icon, onClick }) => (
              <button key={label} type="button" onClick={onClick} aria-label={label} title={label} className="flex h-9 w-9 items-center justify-center text-white/70 transition-colors hover:bg-white/10 hover:text-white">
                <Icon size={15} />
              </button>
            ))}
          </div>

          <ComposableMap projection="geoNaturalEarth1" projectionConfig={{ scale: 160 }} className="h-[620px] w-full">
            <defs>
              <radialGradient id="venue-glow">
                <stop offset="0%" stopColor="#ffb199" stopOpacity={0.9} />
                <stop offset="45%" stopColor="#e2492f" stopOpacity={0.45} />
                <stop offset="100%" stopColor="#e2492f" stopOpacity={0} />
              </radialGradient>
            </defs>
            <ZoomableGroup
              center={zoom.coordinates}
              zoom={zoom.zoom}
              minZoom={MAP_MIN_ZOOM}
              maxZoom={MAP_MAX_ZOOM}
              onMoveStart={() => setPopup(null)}
              onMoveEnd={(pos) => setZoom({ coordinates: pos.coordinates ?? zoom.coordinates, zoom: pos.zoom ?? zoom.zoom })}
            >
              <Geographies geography={worldCountries}>
                {({ geographies }) =>
                  geographies.map((geo) => {
                    const name = (geo.properties as { name?: string } | null)?.name;
                    if (!name) return null;
                    const agg = byCountry.get(name);
                    const isActive = activeCountryName === name;
                    const isHovered = name === hoveredCountry;
                    return (
                      <Geography
                        key={geo.rsmKey}
                        geography={geo}
                        onClick={(e: ReactMouseEvent) => {
                          if (!agg) return;
                          setPopup(isActive ? null : { ...localPoint(e), country: agg });
                          setDetailId(null);
                        }}
                        onMouseEnter={() => agg && setHoveredCountry(name)}
                        onMouseLeave={() => setHoveredCountry((h) => (h === name ? null : h))}
                        style={{
                          fill: !agg ? "rgba(255,255,255,0.035)" : isActive ? "rgba(226,73,47,0.34)" : isHovered ? "rgba(226,73,47,0.24)" : "rgba(226,73,47,0.11)",
                          stroke: !agg ? "rgba(255,255,255,0.07)" : isHovered || isActive ? "rgba(255,146,112,0.6)" : "rgba(255,146,112,0.35)",
                          strokeWidth: 0.4,
                          outline: "none",
                          cursor: agg ? "pointer" : "default",
                          transition: "fill 0.25s ease",
                        }}
                      />
                    );
                  })
                }
              </Geographies>
              {route.map((leg, i) => {
                const slot = drawSeconds / Math.max(route.length, 1);
                const delay = i * slot;
                const duration = Math.max(0.35, slot * 1.6);
                const inv = 1 / Math.sqrt(zoom.zoom);
                return (
                  <g key={`${year}-${i}`}>
                    <Line
                      from={leg.from}
                      to={leg.to}
                      stroke="#ffb199"
                      strokeOpacity={0.6}
                      strokeWidth={1.1 * inv}
                      strokeLinecap="round"
                      className="route-leg"
                      pathLength={1}
                      style={{ animationDelay: `${delay}s`, animationDuration: `${duration}s` }}
                    />
                    <Marker coordinates={leg.to} style={{ pointerEvents: "none" }}>
                      <circle r={3.2 * inv} fill="#fff" className="route-stop" style={{ animationDelay: `${delay + duration * 0.8}s` }} />
                    </Marker>
                  </g>
                );
              })}
              {points.groups.map((p) => {
                const visible = year === null || [...p.years].some((y) => y <= year);
                const lit = year !== null && p.years.has(year);
                // counter-scale by 1/sqrt(zoom): points grow a little as you zoom, never balloon
                const invScale = 1 / Math.sqrt(zoom.zoom);
                const r = (2 + Math.sqrt(p.totalShows / maxShows) * 8) * invScale;
                const isActive = activeKey === p.key;
                const faded = year !== null && !lit;
                const label = p.venues.length === 1 ? p.venues[0].name : `${p.venues[0].city ?? p.venues[0].name}`;
                const sub = `${p.venues.length > 1 ? `${p.venues.length} venues, ` : `${p.venues[0].city ?? ""}, `}${p.totalShows} show${p.totalShows === 1 ? "" : "s"}`;
                return (
                  <Marker
                    key={p.key}
                    coordinates={p.coordinates}
                    onClick={(e: ReactMouseEvent) => visible && openGroup(e, p)}
                    onMouseEnter={(e: ReactMouseEvent) => setHover({ ...localPoint(e), label, sub })}
                    onMouseLeave={() => setHover(null)}
                    className={visible ? "cursor-pointer" : ""}
                    style={{ pointerEvents: visible ? "auto" : "none", opacity: visible ? 1 : 0, transition: "opacity 0.9s ease" }}
                  >
                    {p.precision !== "country" && (
                      <circle
                        r={r * (lit ? 3.6 : 2.4)}
                        fill="url(#venue-glow)"
                        opacity={faded ? 0 : lit ? 1 : 0.55}
                        className={lit ? "venue-pulse" : undefined}
                        style={{ transition: "opacity 0.9s ease" }}
                      />
                    )}
                    <circle
                      r={r}
                      fill={isActive ? "#ffffff" : p.precision === "country" ? "#8a4a3a" : lit ? "#ffd0c0" : "#ff9270"}
                      fillOpacity={faded ? 0.18 : 0.95}
                      style={{ transition: "fill-opacity 0.9s ease, fill 0.9s ease" }}
                      stroke={isActive ? "#ff9270" : "#1a0b06"}
                      strokeWidth={(isActive ? 2 : 0.6) * invScale}
                    />
                  </Marker>
                );
              })}
            </ZoomableGroup>
          </ComposableMap>
          <div className="grain-overlay" />

          <AnimatePresence mode="wait">
            {year !== null && (
              <motion.div
                key={year}
                className="pointer-events-none absolute bottom-20 left-6 z-10"
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
              >
                <p className="chroma font-hero text-6xl font-extrabold leading-none text-white/90">{year}</p>
                <p className="mt-1 text-sm text-white/55">{yearShows} shows, route drawn in date order</p>
                {playing && (
                  <div className="mt-3 h-0.5 w-40 overflow-hidden rounded-full bg-white/10">
                    <motion.div className="h-full bg-ember-light" initial={{ width: 0 }} animate={{ width: "100%" }} transition={{ duration: stepMs / 1000, ease: "linear" }} />
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* hover label */}
          {hover && !popup && (
            <div className="pointer-events-none absolute z-20 -translate-x-1/2 -translate-y-[calc(100%+14px)] whitespace-nowrap rounded-xl bg-ink/85 px-3 py-2 text-center shadow-xl ring-1 ring-white/10 backdrop-blur-xl" style={{ left: hover.x, top: hover.y }}>
              <p className="text-sm text-white">{hover.label}</p>
              <p className="text-[11px] text-white/50">{hover.sub}</p>
            </div>
          )}

          {/* popup */}
          <AnimatePresence>
            {popup && (
              <motion.div
                key={popup.group?.key ?? popup.country?.mapName}
                className="absolute z-30 w-[min(22rem,calc(100%-2rem))] rounded-2xl bg-[#140a0c]/90 p-5 shadow-2xl shadow-black/70 ring-1 ring-ember/30 backdrop-blur-2xl"
                style={{
                  left: `clamp(1rem, ${popup.x + 16}px, calc(100% - min(22rem, 100% - 2rem) - 1rem))`,
                  top: `clamp(1rem, ${popup.y - 60}px, calc(100% - 26rem))`,
                }}
                initial={{ opacity: 0, scale: 0.92, y: 8 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ type: "spring", stiffness: 420, damping: 32 }}
              >
                <button type="button" onClick={() => setPopup(null)} aria-label="Close" className="absolute right-3 top-3 rounded-full p-1.5 text-white/50 hover:bg-white/10 hover:text-white">
                  <X size={14} />
                </button>
                {detailId ? (
                  <VenuePopup
                    venue={(popup.group?.venues ?? popup.country?.venues ?? []).find((v) => v.id === detailId)}
                    detail={detail}
                    onBack={(popup.group?.venues.length ?? 2) > 1 || popup.country ? () => setDetailId(null) : undefined}
                  />
                ) : (
                  <div>
                    <p className="pr-6 font-display text-xl text-white">
                      {popup.country ? popup.country.label : popup.group?.venues[0].city ?? popup.group?.venues[0].name}
                    </p>
                    <p className="text-xs text-white/50">
                      {(popup.group ?? popup.country)!.venues.length} venues, {(popup.group ?? popup.country)!.totalShows} shows
                      {popup.group?.precision === "country" && ", city unresolved"}
                    </p>
                    <ul className="mt-3 max-h-72 space-y-1 overflow-y-auto pr-1">
                      {(popup.group ?? popup.country)!.venues
                        .slice()
                        .sort((a, b) => b.show_count - a.show_count)
                        .map((v) => (
                          <li key={v.id}>
                            <button type="button" onClick={() => setDetailId(v.id)} className="group flex w-full items-center gap-3 rounded-lg px-2 py-1.5 text-left hover:bg-white/[0.06]">
                              <span className="min-w-0 flex-1">
                                <span className="block truncate text-sm text-white">{v.name}</span>
                                <span className="block text-[11px] text-white/45">{v.city} · {v.first_visited?.slice(0, 4)}{v.last_visited && v.first_visited?.slice(0, 4) !== v.last_visited.slice(0, 4) ? `–${v.last_visited.slice(0, 4)}` : ""}</span>
                              </span>
                              <span className="font-mono text-xs text-ember-light">{v.show_count}</span>
                              <ArrowRight size={13} className="text-white/30 group-hover:text-white" />
                            </button>
                          </li>
                        ))}
                    </ul>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* timeline */}
          <div className="absolute inset-x-0 bottom-0 z-10 flex items-center gap-3 bg-gradient-to-t from-ink/90 via-ink/60 to-transparent px-5 pb-4 pt-10">
            <button
              type="button"
              onClick={() => {
                if (!playing && year === null) setYear(allYears[0] ?? null);
                setPopup(null);
                setPlaying((pl) => !pl);
              }}
              aria-label={playing ? "Pause the timeline" : "Play the tour year by year"}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-ink transition-transform hover:scale-105"
            >
              {playing ? <Pause size={14} weight="fill" /> : <Play size={14} weight="fill" />}
            </button>
            <div className="flex min-w-0 flex-1 gap-1 overflow-x-auto">
              <button type="button" onClick={() => { setPlaying(false); setYear(null); }} className={`shrink-0 rounded-full px-2.5 py-1 text-xs ${year === null ? "bg-ember text-white" : "bg-white/[0.07] text-white/60 hover:text-white"}`}>
                All years
              </button>
              {allYears.map((y) => (
                <button
                  key={y}
                  type="button"
                  ref={year === y ? (el) => el?.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" }) : undefined}
                  onClick={() => { setPlaying(false); setYear(y); }}
                  className={`shrink-0 rounded-full px-2.5 py-1 font-mono text-xs transition-colors ${year === y ? "bg-ember text-white" : year !== null && y < year ? "bg-ember/25 text-ember-light" : "bg-white/[0.07] text-white/55 hover:text-white"}`}
                >
                  {y}
                </button>
              ))}
            </div>
            <div className="flex shrink-0 rounded-full bg-white/[0.07] p-0.5 text-[11px]" role="group" aria-label="Playback speed">
              {(["slow", "normal", "fast"] as const).map((sp) => (
                <button
                  key={sp}
                  type="button"
                  onClick={() => setSpeed(sp)}
                  aria-pressed={speed === sp}
                  className={`rounded-full px-2.5 py-1 transition-colors ${speed === sp ? "bg-white text-ink" : "text-white/55 hover:text-white"}`}
                >
                  {sp === "slow" ? "Slow" : sp === "normal" ? "Normal" : "Fast"}
                </button>
              ))}
            </div>
          </div>
        </div>
      </Card>

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

function VenuePopup({ venue, detail, onBack }: { venue?: Venue; detail: VenueDetail | null; onBack?: () => void }) {
  if (!venue) return null;
  return (
    <div>
      {onBack && (
        <button type="button" onClick={onBack} className="mb-2 text-[11px] text-white/45 hover:text-white">
          ← all venues here
        </button>
      )}
      <p className="pr-6 font-display text-xl leading-tight text-white">{venue.name}</p>
      <p className="text-xs text-white/50">
        {venue.city}, {venue.country}
      </p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        <span className="rounded-full bg-ember/20 px-2.5 py-0.5 text-[11px] text-ember-light">
          {venue.show_count} show{venue.show_count === 1 ? "" : "s"}
        </span>
        {venue.kind && <span className="rounded-full bg-white/[0.07] px-2.5 py-0.5 text-[11px] text-white/70">{venue.kind}{venue.is_outdoor ? ", outdoor" : ""}</span>}
        {venue.capacity && <span className="rounded-full bg-white/[0.07] px-2.5 py-0.5 text-[11px] text-white/70">{venue.capacity.toLocaleString("en")} capacity</span>}
      </div>
      {!detail ? (
        <div className="mt-4 h-24 animate-pulse rounded-xl bg-white/[0.05]" />
      ) : (
        <>
          <p className="mt-4 text-[11px] text-white/45">Nights here</p>
          <ul className="mt-1 max-h-40 space-y-0.5 overflow-y-auto pr-1">
            {detail.shows.map((s) => (
              <li key={s.id}>
                <a href={`#/analysis/shows/${s.id}`} className={`flex items-center gap-3 rounded-lg px-2 py-1 text-sm hover:bg-white/[0.06] ${s.songs === 0 ? "pointer-events-none opacity-40" : ""}`}>
                  <span className="font-mono text-[11px] text-white/55">{s.event_date}</span>
                  <span className="min-w-0 flex-1 truncate text-white/80">{s.tour ?? ""}</span>
                  <span className="text-[11px] text-white/40">{s.songs ? `${s.songs} songs` : "no setlist"}</span>
                </a>
              </li>
            ))}
          </ul>
          {detail.top_songs.length > 0 && (
            <>
              <p className="mt-3 text-[11px] text-white/45">Most played here</p>
              <p className="mt-1 text-[13px] leading-relaxed text-white/75">
                {detail.top_songs.map((t) => `${t.name} (${t.plays})`).join(", ")}
              </p>
            </>
          )}
        </>
      )}
    </div>
  );
}
