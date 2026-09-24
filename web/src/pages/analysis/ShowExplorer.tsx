import { useEffect, useMemo, useState, type ReactNode } from "react";
import { ArrowLeft, ArrowRight, Check, CloudRain, MagnifyingGlass, MapPin, Thermometer, Timer, Van, X } from "@phosphor-icons/react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { ShowDetail, ShowSong, ShowSummary } from "../../lib/types";

// The show id lives in the hash (#/analysis/shows/<id>) so a night can be linked to directly.
function readShowId(): string | null {
  const parts = window.location.hash.replace(/^#\/?/, "").split("/");
  return parts[0] === "analysis" && parts[1] === "shows" && parts[2] ? parts[2] : null;
}

function useShowId(): [string | null, (id: string) => void] {
  const [id, setId] = useState<string | null>(readShowId);
  useEffect(() => {
    const onChange = () => setId(readShowId());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return [id, (next) => (window.location.hash = `/analysis/shows/${next}`)];
}

const FORMAT_LABEL: Record<string, string> = {
  festival: "festival slot (estimated)",
  headline: "headline show (estimated)",
  dj_set: "DJ set",
  special: "TV, radio or session",
  incomplete: "setlist incomplete",
};

const pct = (v: number) => `${Math.round(v * 100)}%`;

function formatDate(iso: string) {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", year: "numeric" });
}

function formatDuration(ms: number) {
  const minutes = Math.round(ms / 60000);
  return `${Math.floor(minutes / 60)}h${String(minutes % 60).padStart(2, "0")}`;
}

// What the archive knew about a song before this night: a debut, a return after a long gap,
// or a rarity. Common songs get no label at all, so the labels mean something.
function rarityLabel(song: ShowSong): { text: string; tone: string } | null {
  const r = song.rarity;
  if (!r) return null;
  if (r.first_time) return { text: song.before_release ? "live premiere, before release" : "first time ever", tone: "bg-amber/20 text-amber-light" };
  if (song.before_release) return { text: "not yet released", tone: "bg-amber/15 text-amber-light" };
  if (r.shows_since_last !== null && r.shows_since_last >= 20)
    return { text: `back after ${r.shows_since_last} shows`, tone: "bg-ember/20 text-ember-light" };
  if (r.prior_play_rate !== null && r.prior_play_rate < 0.1)
    return { text: `rare: ${pct(r.prior_play_rate)} of earlier shows`, tone: "bg-white/10 text-white/70" };
  return null;
}

function Fact({ icon: Icon, children }: { icon: typeof MapPin; children: ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-white/[0.06] px-3 py-1 text-[13px] text-white/75 ring-1 ring-white/[0.06]">
      <Icon size={14} className="text-white/45" />
      {children}
    </span>
  );
}

function Setlist({ detail }: { detail: ShowDetail }) {
  let lastSet: string | null = null;
  return (
    <ol className="divide-y divide-white/[0.06]">
      {detail.songs.map((song) => {
        const header = song.set_name && song.set_name !== lastSet ? song.set_name : null;
        lastSet = song.set_name;
        const label = rarityLabel(song);
        return (
          <li key={song.position}>
            {header && <p className="pb-1 pt-4 font-serif text-lg italic text-ember-light first:pt-0">{header}</p>}
            <div className={`flex items-center gap-3 py-2.5 ${song.is_tape ? "opacity-45" : ""}`}>
              <span className="w-6 shrink-0 text-right font-mono text-xs text-white/35">{song.position}</span>
              <div className="min-w-0 flex-1">
                <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[15px] text-white">
                  <span className="truncate">{song.name}</span>
                  {song.is_encore && <span className="rounded-full bg-violet/25 px-2 py-0.5 text-[11px] text-violet-light">encore</span>}
                  {song.is_cover && <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] text-white/70">cover{song.cover_artist ? ` of ${song.cover_artist}` : ""}</span>}
                  {song.is_tape && <span className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] text-white/60">tape</span>}
                  {label && <span className={`rounded-full px-2 py-0.5 text-[11px] ${label.tone}`}>{label.text}</span>}
                </p>
                {(song.guest || song.info || song.album) && (
                  <p className="mt-0.5 truncate text-xs text-white/45">
                    {[song.album && !song.is_cover ? song.album : null, song.guest ? `with ${song.guest}` : null, song.info].filter(Boolean).join(" · ")}
                  </p>
                )}
              </div>
              {/* the model's probability for this song, the night before */}
              <div className="hidden w-32 shrink-0 sm:block" title="Probability the replayed model gave this song the night before">
                {song.predicted_probability !== null ? (
                  <>
                    <div className="h-1.5 overflow-hidden rounded-full bg-white/[0.07]">
                      <div className="h-full rounded-full bg-gradient-to-r from-violet/70 to-violet-light" style={{ width: pct(song.predicted_probability) }} />
                    </div>
                    <p className="mt-1 text-right font-mono text-[11px] text-white/45">
                      {pct(song.predicted_probability)} · #{song.predicted_rank}
                    </p>
                  </>
                ) : (
                  !song.is_tape && <p className="text-right font-mono text-[11px] text-white/30">not scored</p>
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function Replay({ detail }: { detail: ShowDetail }) {
  const r = detail.replay;
  if (!r) {
    return (
      <Card>
        <p className="text-[13px] font-medium text-white/55">The night before</p>
        <p className="mt-3 text-sm leading-relaxed text-white/55">
          No replay for this show. The replay starts after a 60-show warm-up, and shows without a recorded setlist cannot be scored.
        </p>
      </Card>
    );
  }
  return (
    <Card tinted accent="violet">
      <p className="text-[13px] font-medium text-violet-light">The night before, the model said</p>
      <div className="mt-3 flex items-end gap-4">
        <span className="font-hero text-6xl font-extrabold leading-none">{r.hits}<span className="text-white/35">/{r.played}</span></span>
        <span className="pb-1 text-sm leading-snug text-white/60">
          songs called
          <br />
          {pct(r.accuracy)} vs {pct(r.baseline_accuracy)} for "most played so far"
        </span>
      </div>
      <p className="mt-3 text-xs leading-relaxed text-white/45">
        Trained only on the {r.trained_on_shows} shows up to {r.trained_through}. It named as many songs as the night had; ticks are songs that were played.
      </p>
      <ol className="mt-4 space-y-1.5">
        {r.top.map((t, i) => (
          <li key={t.song_id} className={`flex items-center gap-2 text-sm ${i >= r.played ? "opacity-40" : ""}`}>
            <span className="w-5 text-right font-mono text-[11px] text-white/35">{i + 1}</span>
            {t.played ? <Check size={14} weight="bold" className="text-emerald-300" /> : <X size={14} className="text-white/35" />}
            <span className={`min-w-0 flex-1 truncate ${t.played ? "text-white" : "text-white/55"}`}>{t.name}</span>
            <span className="font-mono text-[11px] text-white/45">{pct(t.probability)}</span>
          </li>
        ))}
      </ol>
      {r.unseen_songs.length > 0 && (
        <p className="mt-4 text-xs leading-relaxed text-white/50">
          Never played before this night, so impossible to predict: {r.unseen_songs.join(", ")}.
        </p>
      )}
    </Card>
  );
}

export default function ShowExplorer() {
  const [shows, setShows] = useState<ShowSummary[] | null>(null);
  const [query, setQuery] = useState("");
  const [year, setYear] = useState<string | null>(null);
  const [selectedId, select] = useShowId();
  const [detail, setDetail] = useState<ShowDetail | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.shows().then(setShows).catch(() => setFailed(true));
  }, []);

  const activeId = selectedId ?? shows?.find((s) => s.songs > 0)?.id ?? null;

  useEffect(() => {
    if (!activeId) return;
    setDetail(null);
    api.show(activeId).then(setDetail).catch(() => setFailed(true));
  }, [activeId]);

  const years = useMemo(() => [...new Set((shows ?? []).map((s) => s.event_date.slice(0, 4)))], [shows]);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (shows ?? []).filter(
      (s) =>
        (!year || s.event_date.startsWith(year)) &&
        (!q || [s.venue, s.city, s.country, s.tour, s.event_date].some((f) => f?.toLowerCase().includes(q))),
    );
  }, [shows, query, year]);

  if (failed) return <div className="text-sm text-white/55">The show archive could not be loaded. Is the API running?</div>;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.arenaLasersWide.src} alt={PHOTOS.arenaLasersWide.alt} size={56} accent="ember" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">Shows</h1>
        </div>
        <p className="text-sm leading-relaxed text-white/50 sm:text-right">
          {shows ? `${shows.length} nights, ${shows.filter((s) => s.songs > 0).length} with a setlist` : "Loading the archive"}
          <br />
          each one replayed against what the model predicted the night before
        </p>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-6 xl:grid-cols-[340px_1fr]">
        {/* The archive */}
        <Card className="xl:sticky xl:top-24 xl:self-start">
          <label className="flex items-center gap-2 rounded-full bg-white/[0.05] px-3.5 py-2 ring-1 ring-white/10 focus-within:ring-white/30">
            <MagnifyingGlass size={15} className="text-white/45" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="City, venue, tour, date"
              className="w-full bg-transparent text-sm text-white outline-none placeholder:text-white/35"
            />
          </label>
          <div className="mt-3 flex gap-1.5 overflow-x-auto pb-1">
            <button type="button" onClick={() => setYear(null)} className={`shrink-0 rounded-full px-2.5 py-1 text-xs ${year === null ? "bg-white text-ink" : "bg-white/[0.06] text-white/60 hover:text-white"}`}>
              All
            </button>
            {years.map((y) => (
              <button key={y} type="button" onClick={() => setYear(y === year ? null : y)} className={`shrink-0 rounded-full px-2.5 py-1 font-mono text-xs ${year === y ? "bg-white text-ink" : "bg-white/[0.06] text-white/60 hover:text-white"}`}>
                {y}
              </button>
            ))}
          </div>
          <ul className="mt-3 max-h-[62vh] space-y-0.5 overflow-y-auto pr-1">
            {filtered.map((s) => {
              const active = s.id === activeId;
              return (
                <li key={s.id}>
                  <button
                    type="button"
                    onClick={() => select(s.id)}
                    disabled={s.songs === 0}
                    className={`flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left transition-colors ${active ? "bg-ember/20 ring-1 ring-ember/40" : "hover:bg-white/[0.05]"} disabled:cursor-not-allowed disabled:opacity-35`}
                  >
                    <span className="w-[4.6rem] shrink-0 font-mono text-[11px] text-white/45">{s.event_date}</span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm text-white">{s.city}</span>
                      <span className="block truncate text-xs text-white/45">{s.songs === 0 ? "no setlist recorded" : s.venue}</span>
                    </span>
                    {s.replay_accuracy !== null && <span className="shrink-0 font-mono text-[11px] text-violet-light">{pct(s.replay_accuracy)}</span>}
                  </button>
                </li>
              );
            })}
            {shows && filtered.length === 0 && <li className="px-3 py-6 text-center text-sm text-white/45">No show matches.</li>}
          </ul>
        </Card>

        {/* One night */}
        <div className="min-w-0 space-y-6">
          {!detail ? (
            <div className="h-[60vh] animate-pulse rounded-[26px] bg-white/[0.04]" />
          ) : (
            <>
              <Card tinted accent="ember">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="font-serif text-2xl italic text-ember-light">{formatDate(detail.event_date)}</p>
                    <h2 className="mt-1 font-display text-3xl font-semibold tracking-tight sm:text-4xl">{detail.venue.name}</h2>
                    <p className="mt-1 text-white/60">
                      {detail.venue.city}, {detail.venue.country}
                      {detail.tour ? ` · ${detail.tour}` : ""}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button type="button" disabled={!detail.previous_id} onClick={() => detail.previous_id && select(detail.previous_id)} aria-label="Previous show" className="rounded-full p-2.5 ring-1 ring-white/15 hover:bg-white/[0.07] disabled:opacity-30">
                      <ArrowLeft size={16} />
                    </button>
                    <button type="button" disabled={!detail.next_id} onClick={() => detail.next_id && select(detail.next_id)} aria-label="Next show" className="rounded-full p-2.5 ring-1 ring-white/15 hover:bg-white/[0.07] disabled:opacity-30">
                      <ArrowRight size={16} />
                    </button>
                  </div>
                </div>
                <div className="mt-5 flex flex-wrap gap-2">
                  {detail.format && (
                    <span
                      title={detail.format.signals.join("; ")}
                      className={`inline-flex items-center rounded-full px-3 py-1 text-[13px] ring-1 ${detail.format.kind === "festival" ? "bg-amber/20 text-amber-light ring-amber/30" : "bg-white/[0.06] text-white/75 ring-white/[0.06]"}`}
                    >
                      {FORMAT_LABEL[detail.format.kind] ?? detail.format.kind}
                    </span>
                  )}
                  {detail.venue.kind && <Fact icon={MapPin}>{detail.venue.kind}{detail.venue.is_outdoor ? ", outdoor" : ""}{detail.venue.capacity ? `, ${detail.venue.capacity.toLocaleString("en")} capacity` : ""}</Fact>}
                  {detail.weather?.temp_max_c != null && <Fact icon={Thermometer}>{Math.round(detail.weather.temp_max_c)}° / {Math.round(detail.weather.temp_min_c ?? 0)}°</Fact>}
                  {detail.weather?.precipitation_mm != null && detail.weather.precipitation_mm > 0 && <Fact icon={CloudRain}>{detail.weather.precipitation_mm} mm rain</Fact>}
                  {detail.derived?.known_duration_ms != null && <Fact icon={Timer}>{formatDuration(detail.derived.known_duration_ms)} of music</Fact>}
                  {detail.derived?.travel_km != null && detail.derived.days_since_previous != null && (
                    <Fact icon={Van}>{Math.round(detail.derived.travel_km).toLocaleString("en")} km in {detail.derived.days_since_previous} days</Fact>
                  )}
                </div>
                {detail.url && (
                  <a href={detail.url} target="_blank" rel="noreferrer" className="mt-4 inline-block text-xs text-white/45 underline decoration-white/20 underline-offset-4 hover:text-white">
                    Source: setlist.fm
                  </a>
                )}
              </Card>

              <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1.35fr_1fr]">
                <Card>
                  <div className="flex items-baseline justify-between">
                    <p className="text-[13px] font-medium text-white/55">Setlist</p>
                    <p className="hidden text-[11px] text-white/35 sm:block">model's probability, night before</p>
                  </div>
                  <div className="mt-3">
                    <Setlist detail={detail} />
                  </div>
                </Card>
                <Replay detail={detail} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
