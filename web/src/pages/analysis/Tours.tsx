import { useEffect, useMemo, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { TourSummary } from "../../lib/types";

function formatShort(iso: string | null) {
  if (!iso) return "unknown";
  return new Date(iso + "T00:00:00").toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

function spanMonths(startIso: string | null, endIso: string | null) {
  if (!startIso || !endIso) return null;
  const start = new Date(startIso + "T00:00:00").getTime();
  const end = new Date(endIso + "T00:00:00").getTime();
  return Math.max(1, Math.round((end - start) / (86400000 * 30.4)));
}

export default function Tours() {
  const [tours, setTours] = useState<TourSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  useEffect(() => {
    api
      .tours()
      .then((data) => {
        setTours(data);
        const biggest = data.slice().sort((a, b) => b.show_count - a.show_count)[0];
        if (biggest) setSelectedId(biggest.tour_id);
      })
      .catch(() => {});
  }, []);

  const maxShows = Math.max(...tours.map((t) => t.show_count), 1);
  const selected = tours.find((t) => t.tour_id === selectedId) ?? null;

  // Real totals across the tours the database assigns. Shows with no tour are excluded by
  // the endpoint itself, so this is deliberately "concerts on a named tour", not all 767.
  const totals = useMemo(() => {
    const shows = tours.reduce((sum, t) => sum + t.show_count, 0);
    const withAvg = tours.filter((t) => t.avg_songs !== null);
    return {
      shows,
      tours: tours.length,
      longest: tours.slice().sort((a, b) => b.show_count - a.show_count)[0] ?? null,
      avgSongsRange:
        withAvg.length > 0
          ? [
              Math.min(...withAvg.map((t) => t.avg_songs as number)),
              Math.max(...withAvg.map((t) => t.avg_songs as number)),
            ]
          : null,
    };
  }, [tours]);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.arenaLasersWide.src} alt={PHOTOS.arenaLasersWide.alt} size={56} accent="ember" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">Tours</h1>
        </div>
        <p className="text-sm leading-relaxed text-white/50 sm:text-right">
          {totals.tours} named tours · {totals.shows} concerts assigned to one
          <br />
          bar width = concerts on that tour
        </p>
      </div>

      <div className="mt-10 grid grid-cols-6 gap-6">
        <Card className="anim-fade-in-up col-span-6 lg:col-span-4">
          <div className="text-sm font-medium text-white/55">
            Every tour, oldest first
          </div>
          <div className="mt-6 space-y-4">
            {tours.map((tour, i) => {
              const active = tour.tour_id === selectedId;
              return (
                <button
                  key={tour.tour_id}
                  type="button"
                  onClick={() => setSelectedId(tour.tour_id)}
                  className={`anim-fade-in-up block w-full rounded-xl border p-3 text-left transition-colors ${
                    active ? "border-ember/50 bg-ember/10" : "border-transparent hover:border-white/15"
                  }`}
                  style={{ animationDelay: `${i * 0.05}s` }}
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="truncate font-display text-base font-medium text-white">{tour.name}</span>
                    <span className="shrink-0 font-mono text-xs text-white/40">
                      {formatShort(tour.date_start)} to {formatShort(tour.date_end)}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center gap-3">
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/5">
                      <div
                        className="anim-width-in h-full rounded-full bg-gradient-to-r from-ember-dark via-ember to-ember-light"
                        style={{ width: `${(tour.show_count / maxShows) * 100}%`, animationDelay: `${0.1 + i * 0.05}s` }}
                      />
                    </div>
                    <span className="w-24 shrink-0 text-right font-mono text-xs text-white/50">
                      {tour.show_count} shows
                    </span>
                  </div>
                </button>
              );
            })}
            {tours.length === 0 && (
              <p className="font-mono text-xs text-white/30">Loading tours…</p>
            )}
          </div>
        </Card>

        {selected && (
          <Card tinted accent="ember" className="anim-fade-in-up col-span-6 lg:col-span-2" style={{ animationDelay: "0.1s" }}>
            <div className="text-[13px] font-medium text-white/50">Selected tour</div>
            <div className="mt-2 font-display text-3xl font-bold leading-tight">{selected.name}</div>
            <div className="mt-1 font-mono text-xs text-white/50">
              {selected.year_start}
              {selected.year_end !== selected.year_start ? ` to ${selected.year_end}` : ""}
            </div>

            <div className="mt-6 grid grid-cols-2 gap-3">
              <div className="rounded-xl border border-white/10 bg-ink/30 p-3">
                <div className="text-[13px] font-medium text-white/55">Concerts</div>
                <div className="mt-1 font-display text-3xl font-bold">{selected.show_count}</div>
              </div>
              <div className="rounded-xl border border-white/10 bg-ink/30 p-3">
                <div className="text-[13px] font-medium text-white/55">Venues</div>
                <div className="mt-1 font-display text-3xl font-bold">{selected.venue_count}</div>
              </div>
              <div className="rounded-xl border border-white/10 bg-ink/30 p-3">
                <div className="text-[13px] font-medium text-white/55">Countries</div>
                <div className="mt-1 font-display text-3xl font-bold">{selected.country_count}</div>
              </div>
              <div className="rounded-xl border border-white/10 bg-ink/30 p-3">
                <div className="text-[13px] font-medium text-white/55">Avg songs</div>
                <div className="mt-1 font-display text-3xl font-bold">{selected.avg_songs ?? "N/A"}</div>
              </div>
              <div className="rounded-xl border border-white/10 bg-ink/30 p-3">
                <div className="text-[13px] font-medium text-white/55">Travelled</div>
                <div className="mt-1 font-display text-3xl font-bold">
                  {selected.travel_km != null ? selected.travel_km.toLocaleString() : "N/A"}
                  <span className="ml-1 font-mono text-sm font-normal text-white/40">km</span>
                </div>
                <div className="font-mono text-[10px] text-white/30">
                  {selected.legs_known ?? 0} of {selected.legs_total ?? 0} legs measured
                </div>
              </div>
              <div className="rounded-xl border border-white/10 bg-ink/30 p-3">
                <div className="text-[13px] font-medium text-white/55">Longest hop</div>
                <div className="mt-1 font-display text-3xl font-bold">
                  {selected.longest_hop_km != null ? selected.longest_hop_km.toLocaleString() : "N/A"}
                  <span className="ml-1 font-mono text-sm font-normal text-white/40">km</span>
                </div>
                <div className="font-mono text-[10px] text-white/30">between two dates</div>
              </div>
            </div>

            <p className="mt-4 text-[13px] leading-relaxed text-white/25">
              Distance is straight-line between the cities of consecutive shows, counted only
              where both venues have coordinates, so it is a floor rather than a full mileage.
            </p>

            <div className="mt-5 font-mono text-xs text-white/40">
              Ran {spanMonths(selected.date_start, selected.date_end) ?? "?"} months, from{" "}
              {formatShort(selected.date_start)} to {formatShort(selected.date_end)}.
            </div>
          </Card>
        )}

        {/* How the average set grew tour by tour: one real number per tour, in order. */}
        <Card className="anim-fade-in-up col-span-6" style={{ animationDelay: "0.2s" }}>
          <div className="text-[13px] font-medium text-white/55">
            Average songs per show, tour by tour
          </div>
          <div className="mt-6 flex items-end gap-2 overflow-x-auto sm:gap-4" style={{ height: 190 }}>
            {tours.map((tour, i) => {
              const value = tour.avg_songs ?? 0;
              const max = Math.max(...tours.map((t) => t.avg_songs ?? 0), 1);
              const heightPct = Math.max(6, (value / max) * 100);
              const active = tour.tour_id === selectedId;
              return (
                <button
                  key={tour.tour_id}
                  type="button"
                  onClick={() => setSelectedId(tour.tour_id)}
                  className="flex flex-1 flex-col items-center justify-end gap-2"
                  style={{ height: "100%" }}
                >
                  <span className="font-mono text-xs text-white/60">{tour.avg_songs ?? "N/A"}</span>
                  <div
                    className={`anim-bar-in w-full rounded-t-md bg-gradient-to-t transition-opacity ${
                      active ? "from-ember-dark via-ember to-ember-light" : "from-ember-dark/50 via-ember/50 to-ember-light/50 hover:opacity-80"
                    }`}
                    style={{ height: `${heightPct}%`, animationDelay: `${0.1 + i * 0.05}s` }}
                  />
                  <span className="text-[13px] font-medium line-clamp-2 text-center leading-tight text-white/55">
                    {tour.name}
                  </span>
                </button>
              );
            })}
          </div>
        </Card>

        <PhotoPanel
          photo={PHOTOS.arenaLasersWide}
          accent="ember"
          tag="eighteen years on the road"
          className="col-span-6 h-[19rem]"
          focus="center 45%"
          style={{ animationDelay: "0.3s" }}
        />
      </div>
    </div>
  );
}
