import { motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import { albumColour } from "../../lib/albumColours";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { Popularity } from "../../lib/types";

const pct = (v: number) => `${Math.round(v * 100)}%`;
const fmt = (n: number) => (n >= 1000 ? `${Math.round(n / 1000)}k` : String(n));

export default function HitsAndRarities() {
  const [data, setData] = useState<Popularity | null>(null);
  const [recent, setRecent] = useState(true);
  const [hover, setHover] = useState<number | null>(null);
  useEffect(() => {
    api.popularity().then(setData).catch(() => {});
  }, []);

  const songs = data?.songs ?? [];
  const rate = (s: Popularity["songs"][number]) => (recent ? s.recent_live_rate : s.live_rate);
  const [minL, maxL] = useMemo(() => {
    const ls = songs.map((s) => Math.log10(Math.max(1, s.listeners)));
    return [Math.min(...ls, 0), Math.max(...ls, 1)];
  }, [songs]);

  if (!data) return <div className="h-[60vh] animate-pulse rounded-[26px] bg-white/[0.04]" />;
  if (songs.length === 0)
    return <div className="text-sm text-white/55">No listening data yet. Run: uv run python -m undercurrents.clustering.popularity</div>;

  const W = 1000;
  const H = 520;
  const pad = 40;
  const x = (listeners: number) => pad + ((Math.log10(Math.max(1, listeners)) - minL) / (maxL - minL)) * (W - 2 * pad);
  const y = (r: number) => H - pad - r * (H - 2 * pad);
  const medianListeners = songs.map((s) => s.listeners).sort((a, b) => a - b)[Math.floor(songs.length / 2)];
  const loved = songs.filter((s) => rate(s) < 0.1).slice(0, 8);
  const staples = songs.filter((s) => rate(s) >= 0.8).slice(0, 8);
  const h = hover !== null ? songs[hover] : null;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.singerConfetti.src} alt={PHOTOS.singerConfetti.alt} size={56} accent="ember" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">Hits and Rarities</h1>
        </div>
        <p className="max-w-md text-sm leading-relaxed text-white/50 sm:text-right">
          What people listen to, against what the band plays live
          <br />
          {songs.length} songs with listening data
        </p>
      </div>

      <Card className="mt-10">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-[13px] font-medium text-white/55">Listeners (log scale) against the share of shows that played the song</p>
          <div className="flex rounded-full bg-white/[0.06] p-1 text-xs">
            {[
              { v: true, label: `last ${data.recent_window} shows` },
              { v: false, label: "all time" },
            ].map((o) => (
              <button key={o.label} type="button" onClick={() => setRecent(o.v)} className={`rounded-full px-3 py-1 transition-colors ${recent === o.v ? "bg-white text-ink" : "text-white/60 hover:text-white"}`}>
                {o.label}
              </button>
            ))}
          </div>
        </div>
        <div className="relative mt-4" onPointerLeave={() => setHover(null)}>
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full">
            <line x1={x(medianListeners)} x2={x(medianListeners)} y1={pad} y2={H - pad} stroke="white" strokeOpacity={0.12} strokeDasharray="4 5" />
            <line x1={pad} x2={W - pad} y1={y(0.5)} y2={y(0.5)} stroke="white" strokeOpacity={0.12} strokeDasharray="4 5" />
            <text x={W - pad} y={pad + 14} textAnchor="end" fontSize={13} fill="rgba(255,255,255,0.35)" fontStyle="italic">loved and played</text>
            <text x={W - pad} y={y(0.12)} textAnchor="end" fontSize={13} fill="rgba(255,255,255,0.35)" fontStyle="italic">loved, rarely played</text>
            <text x={pad + 6} y={pad + 14} fontSize={13} fill="rgba(255,255,255,0.35)" fontStyle="italic">stage songs</text>
            <text x={pad + 6} y={y(0.12)} fontSize={13} fill="rgba(255,255,255,0.35)" fontStyle="italic">deep cuts</text>
            {[0, 0.25, 0.5, 0.75, 1].map((t) => (
              <text key={t} x={pad - 8} y={y(t) + 4} textAnchor="end" fontSize={11} fill="rgba(255,255,255,0.4)">{pct(t)}</text>
            ))}
            {songs.map((s, i) => (
              <motion.circle
                key={s.song_id}
                initial={false}
                animate={{ cx: x(s.listeners), cy: y(rate(s)) }}
                transition={{ type: "spring", stiffness: 120, damping: 18 }}
                r={hover === i ? 9 : 6}
                fill={albumColour(s.album)}
                fillOpacity={hover === null || hover === i ? 0.9 : 0.35}
                stroke="#0d0710"
                strokeWidth={1.5}
                onPointerEnter={() => setHover(i)}
                className="cursor-pointer"
              />
            ))}
          </svg>
          {h && (
            <div
              className="pointer-events-none absolute z-10 w-60 rounded-2xl bg-ink/85 p-3 text-sm shadow-2xl ring-1 ring-white/10 backdrop-blur-xl"
              style={{ left: `clamp(0px, calc(${(x(h.listeners) / W) * 100}% + 12px), calc(100% - 15rem))`, top: `calc(${(y(rate(h)) / H) * 100}% - 20px)` }}
            >
              <p className="text-white">{h.name}</p>
              <p className="text-xs" style={{ color: albumColour(h.album) }}>{h.album ?? "no record on file"}</p>
              <p className="mt-2 text-xs text-white/65">
                {h.listeners.toLocaleString("en")} listeners, {h.listens.toLocaleString("en")} listens
              </p>
              <p className="text-xs text-white/65">
                played at {pct(h.recent_live_rate)} of the last {data.recent_window} shows, {pct(h.live_rate)} all time
              </p>
              {h.last_played && <p className="text-xs text-white/40">last played {h.last_played}</p>}
            </div>
          )}
        </div>
        {data.source && <p className="mt-3 text-xs leading-relaxed text-white/40">{data.source}</p>}
      </Card>

      <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card tinted accent="ember">
          <p className="text-[13px] font-medium text-ember-light">Loved, rarely played</p>
          <p className="mt-1 text-xs text-white/45">Most listened songs in under 10% of {recent ? `the last ${data.recent_window} shows` : "all shows"}</p>
          <ul className="mt-4 space-y-2">
            {loved.map((s) => (
              <li key={s.song_id} className="flex items-center gap-3">
                <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: albumColour(s.album) }} />
                <span className="min-w-0 flex-1 truncate text-sm text-white">{s.name}</span>
                <span className="font-mono text-[11px] text-white/45">{fmt(s.listeners)} listeners</span>
                <span className="w-10 text-right font-mono text-[11px] text-ember-light">{pct(rate(s))}</span>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <p className="text-[13px] font-medium text-white/55">Played nearly every night</p>
          <p className="mt-1 text-xs text-white/45">In 80% or more of {recent ? `the last ${data.recent_window} shows` : "all shows"}, by listeners</p>
          <ul className="mt-4 space-y-2">
            {staples.map((s) => (
              <li key={s.song_id} className="flex items-center gap-3">
                <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: albumColour(s.album) }} />
                <span className="min-w-0 flex-1 truncate text-sm text-white">{s.name}</span>
                <span className="font-mono text-[11px] text-white/45">{fmt(s.listeners)} listeners</span>
                <span className="w-10 text-right font-mono text-[11px] text-violet-light">{pct(rate(s))}</span>
              </li>
            ))}
            {staples.length === 0 && <li className="text-sm text-white/45">No song reaches 80% in this window.</li>}
          </ul>
        </Card>
      </div>
    </div>
  );
}
