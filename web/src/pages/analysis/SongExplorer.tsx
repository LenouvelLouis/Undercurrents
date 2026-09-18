import { useEffect, useMemo, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { SetlistFeatureSummary, SongFeature } from "../../lib/types";

const SORTS = [
  { key: "play_count", label: "Most played" },
  { key: "current_streak", label: "Longest run now" },
  { key: "longest_gap_days", label: "Longest absence" },
  { key: "opener_count", label: "Opens the show" },
  { key: "encore_count", label: "Closes the show" },
  { key: "last_played", label: "Most recent" },
] as const;

type SortKey = (typeof SORTS)[number]["key"];

const ERA_COLORS: Record<string, string> = {
  Innerspeaker: "#d99a3f",
  Lonerism: "#e2492f",
  Currents: "#a531d6",
  "Slow Rush -> Deadbeat": "#ff9270",
};

function formatDate(iso: string | null) {
  if (!iso) return "never";
  return new Date(iso + "T00:00:00").toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

function formatGap(days: number | null) {
  if (days == null) return "N/A";
  if (days < 400) return `${days}d`;
  return `${(days / 365.25).toFixed(1)}y`;
}

export default function SongExplorer() {
  const [songs, setSongs] = useState<SongFeature[]>([]);
  const [summary, setSummary] = useState<SetlistFeatureSummary | null>(null);
  const [sort, setSort] = useState<SortKey>("play_count");
  const [query, setQuery] = useState("");

  useEffect(() => {
    api.songFeatures().then(setSongs).catch(() => {});
    api.setlistFeatureSummary().then(setSummary).catch(() => {});
  }, []);

  const sorted = useMemo(() => {
    const filtered = query
      ? songs.filter((s) => s.song_name.toLowerCase().includes(query.toLowerCase()))
      : songs;
    return filtered.slice().sort((a, b) => {
      if (sort === "last_played") {
        return (b.last_played ?? "").localeCompare(a.last_played ?? "");
      }
      return (Number(b[sort] ?? 0)) - (Number(a[sort] ?? 0));
    });
  }, [songs, sort, query]);

  const top = sorted.slice(0, 30);
  const maxOfSort = Math.max(
    ...top.map((s) => (sort === "last_played" ? 1 : Number(s[sort] ?? 0))),
    1,
  );

  // Novelty per year, from the endpoint that computes it over the derived table.
  const novelty = summary?.by_year ?? [];
  const maxNovelty = Math.max(...novelty.map((y) => y.avg_novelty), 0.01);

  return (
    <div>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.guitaristConfetti.src} alt={PHOTOS.guitaristConfetti.alt} size={56} accent="ember" />
          <h1 className="font-display text-6xl font-bold">
            Song
            <br />
            Explorer
          </h1>
        </div>
        <p className="max-w-sm text-right font-mono text-xs italic text-white/40">
          {songs.length} songs, each with its own history
          <br />
          recomputed from every performance on record
        </p>
      </div>

      {/* Headline numbers about how much a setlist actually changes. */}
      {summary && summary.shows > 0 && (
        <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-5">
          <Card className="anim-fade-in-up">
            <div className="font-mono text-[10px] uppercase tracking-widest text-white/35">Songs per show</div>
            <div className="mt-1 font-display text-3xl font-bold">{summary.avg_songs ?? "N/A"}</div>
          </Card>
          <Card className="anim-fade-in-up" style={{ animationDelay: "0.04s" }}>
            <div className="font-mono text-[10px] uppercase tracking-widest text-white/35">Changes each night</div>
            <div className="mt-1 font-display text-3xl font-bold">
              {summary.avg_novelty != null ? `${Math.round(summary.avg_novelty * 100)}%` : "N/A"}
            </div>
            <div className="font-mono text-[10px] text-white/30">of the set is new</div>
          </Card>
          <Card className="anim-fade-in-up" style={{ animationDelay: "0.08s" }}>
            <div className="font-mono text-[10px] uppercase tracking-widest text-white/35">Days between shows</div>
            <div className="mt-1 font-display text-3xl font-bold">{summary.avg_gap_days ?? "N/A"}</div>
          </Card>
          <Card className="anim-fade-in-up" style={{ animationDelay: "0.12s" }}>
            <div className="font-mono text-[10px] uppercase tracking-widest text-white/35">Typical hop</div>
            <div className="mt-1 font-display text-3xl font-bold">
              {summary.avg_travel_km != null ? `${summary.avg_travel_km.toLocaleString()}` : "N/A"}
              <span className="ml-1 font-mono text-sm font-normal text-white/40">km</span>
            </div>
            <div className="font-mono text-[10px] text-white/30">{summary.legs_known ?? 0} legs measured</div>
          </Card>
          <Card className="anim-fade-in-up" style={{ animationDelay: "0.16s" }}>
            <div className="font-mono text-[10px] uppercase tracking-widest text-white/35">Total travelled</div>
            <div className="mt-1 font-display text-3xl font-bold">
              {summary.total_travel_km != null
                ? `${Math.round(summary.total_travel_km / 1000)}k`
                : "N/A"}
              <span className="ml-1 font-mono text-sm font-normal text-white/40">km</span>
            </div>
            <div className="font-mono text-[10px] text-white/30">known legs only</div>
          </Card>
        </div>
      )}

      <div className="mt-6 grid grid-cols-5 gap-6">
        <Card className="anim-fade-in-up col-span-5 lg:col-span-3" accent="ember">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="font-mono text-sm uppercase tracking-widest text-white/40">Every song</div>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter…"
              className="w-40 rounded-full border border-white/15 bg-white/5 px-4 py-1.5 font-mono text-xs text-white outline-none focus:border-ember"
            />
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {SORTS.map((s) => (
              <button
                key={s.key}
                type="button"
                onClick={() => setSort(s.key)}
                className={`rounded-full border px-3 py-1 font-mono text-[10px] uppercase tracking-widest transition-colors ${
                  sort === s.key
                    ? "border-ember/60 bg-ember/15 text-white"
                    : "border-white/15 text-white/45 hover:border-white/35 hover:text-white/80"
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>

          <div className="mt-5 space-y-2.5">
            {top.map((song, i) => {
              const value = sort === "last_played" ? 0 : Number(song[sort] ?? 0);
              return (
                <div key={song.song_id} className="anim-fade-in-up" style={{ animationDelay: `${Math.min(i, 20) * 0.02}s` }}>
                  <div className="flex items-center gap-3">
                    <span
                      className="h-2 w-2 shrink-0 rounded-full"
                      style={{ backgroundColor: ERA_COLORS[song.dominant_era ?? ""] ?? "rgba(255,255,255,0.25)" }}
                      title={song.dominant_era ?? "unknown era"}
                    />
                    <span className="min-w-0 shrink grow-[12] basis-0 truncate font-display text-sm font-medium">
                      {song.song_name}
                    </span>
                    {sort !== "last_played" && (
                      <div className="h-1.5 min-w-0 shrink grow-[14] basis-0 overflow-hidden rounded-full bg-white/[0.04]">
                        <div
                          className="anim-width-in h-full rounded-full bg-gradient-to-r from-ember-dark via-ember to-ember-light"
                          style={{ width: `${Math.max(2, (value / maxOfSort) * 100)}%` }}
                        />
                      </div>
                    )}
                    <span className="w-14 shrink-0 text-right font-mono text-[11px] text-white/55">
                      {sort === "longest_gap_days"
                        ? formatGap(song.longest_gap_days)
                        : sort === "last_played"
                          ? formatDate(song.last_played)
                          : value}
                    </span>
                  </div>
                  <div className="ml-5 mt-1 flex flex-wrap gap-x-4 font-mono text-[10px] text-white/25">
                    <span>{song.play_count} plays</span>
                    <span>{formatDate(song.first_played)} to {formatDate(song.last_played)}</span>
                    {song.current_streak > 0 && <span className="text-ember-light">on a run of {song.current_streak}</span>}
                    {song.opener_count > 0 && <span>opened {song.opener_count}x</span>}
                    {song.encore_count > 0 && <span>encore {song.encore_count}x</span>}
                  </div>
                </div>
              );
            })}
            {top.length === 0 && <p className="font-mono text-xs text-white/30">No song matches that filter.</p>}
          </div>
        </Card>

        <div className="col-span-5 space-y-6 lg:col-span-2">
          {novelty.length > 0 && (
            <Card className="anim-fade-in-up" accent="ember" style={{ animationDelay: "0.1s" }}>
              <div className="font-mono text-sm uppercase tracking-widest text-white/40">
                How much the set changes
              </div>
              <p className="mt-2 font-mono text-[11px] leading-relaxed text-white/35">
                Share of each night's songs that were not played the previous night, averaged
                per year. A low bar is a locked-in tour; a high one is a band rotating songs.
              </p>
              <div className="mt-6 flex items-end gap-1.5" style={{ height: 150 }}>
                {novelty.map((year, i) => (
                  <div key={year.year} className="flex flex-1 flex-col items-center justify-end gap-1.5" style={{ height: "100%" }} title={`${year.year}: ${Math.round(year.avg_novelty * 100)}% new, ${year.shows} shows`}>
                    <span className="font-mono text-[9px] text-white/40">
                      {Math.round(year.avg_novelty * 100)}
                    </span>
                    <div
                      className="anim-bar-in w-full rounded-t-[3px] bg-gradient-to-t from-ember-dark via-ember to-ember-light"
                      style={{
                        height: `${Math.max(4, (year.avg_novelty / maxNovelty) * 100)}%`,
                        animationDelay: `${0.1 + i * 0.03}s`,
                      }}
                    />
                    <span className="font-mono text-[9px] text-white/30">{String(year.year).slice(2)}</span>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <PhotoPanel
            photo={PHOTOS.guitaristConfetti}
            accent="ember"
            tag="the same songs, never the same night"
            className="h-[17rem]"
            focus="center 40%"
            style={{ animationDelay: "0.2s" }}
          />
        </div>
      </div>
    </div>
  );
}
