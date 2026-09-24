import { motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { ModelHealth as Health } from "../../lib/types";

const pct = (v: number) => `${Math.round(v * 100)}%`;
const ROLL = 12;

function rolling(values: number[], window: number) {
  return values.map((_, i) => {
    const slice = values.slice(Math.max(0, i - window + 1), i + 1);
    return slice.reduce((a, b) => a + b, 0) / slice.length;
  });
}

// When the model says p, how often is the song played? Points on the diagonal are honest
// probabilities; above it the model was too cautious, below it too confident.
function Calibration({ bins }: { bins: Health["calibration"] }) {
  const [hover, setHover] = useState<number | null>(null);
  const S = 300;
  const pts = bins.filter((b) => b.mean_predicted !== null && b.observed_rate !== null);
  const maxCount = Math.max(...pts.map((b) => b.count), 1);
  const x = (v: number) => 30 + v * (S - 40);
  const y = (v: number) => S - 30 - v * (S - 40);
  const line = pts.map((b, i) => `${i ? "L" : "M"}${x(b.mean_predicted!)},${y(b.observed_rate!)}`).join(" ");
  const h = hover !== null ? pts[hover] : null;
  return (
    <div className="relative">
      <svg viewBox={`0 0 ${S} ${S}`} className="mx-auto w-full max-w-[26rem]">
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <g key={t}>
            <line x1={x(0)} x2={x(1)} y1={y(t)} y2={y(t)} stroke="white" strokeOpacity={0.06} />
            <line x1={x(t)} x2={x(t)} y1={y(0)} y2={y(1)} stroke="white" strokeOpacity={0.06} />
            <text x={x(t)} y={S - 12} textAnchor="middle" fontSize={9} fill="rgba(255,255,255,0.4)">{pct(t)}</text>
            <text x={18} y={y(t) + 3} textAnchor="middle" fontSize={9} fill="rgba(255,255,255,0.4)">{pct(t)}</text>
          </g>
        ))}
        <line x1={x(0)} y1={y(0)} x2={x(1)} y2={y(1)} stroke="white" strokeOpacity={0.35} strokeDasharray="4 4" />
        <motion.path d={line} fill="none" stroke="#e2a6ff" strokeWidth={2} initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.4 }} />
        {pts.map((b, i) => (
          <circle
            key={i}
            cx={x(b.mean_predicted!)}
            cy={y(b.observed_rate!)}
            r={3 + Math.sqrt(b.count / maxCount) * 9}
            fill="#a531d6"
            fillOpacity={hover === i ? 0.95 : 0.6}
            stroke="#e2a6ff"
            onPointerEnter={() => setHover(i)}
            onPointerLeave={() => setHover(null)}
            className="cursor-pointer"
          />
        ))}
      </svg>
      <p className="mt-1 text-center text-[11px] text-white/40">predicted probability → how often played</p>
      {h && (
        <div className="absolute right-2 top-2 rounded-xl bg-ink/85 px-3 py-2 text-xs ring-1 ring-white/10 backdrop-blur-xl">
          <p className="text-white">Said {pct(h.bin_start)} to {pct(h.bin_end)}</p>
          <p className="text-white/60">
            {h.count.toLocaleString("en")} predictions, played {pct(h.observed_rate!)} of the time (avg said {pct(h.mean_predicted!)})
          </p>
        </div>
      )}
    </div>
  );
}

function Timeline({ series }: { series: Health["series"] }) {
  const [hover, setHover] = useState<number | null>(null);
  const model = useMemo(() => rolling(series.map((s) => s.accuracy), ROLL), [series]);
  const base = useMemo(() => rolling(series.map((s) => s.baseline), ROLL), [series]);
  const W = 1000;
  const H = 260;
  const x = (i: number) => (i / (series.length - 1)) * W;
  const y = (v: number) => H - v * H;
  const path = (vals: number[]) => vals.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const yearStarts = series.map((s, i) => ({ i, y: s.event_date.slice(0, 4) })).filter((s, k, arr) => k === 0 || s.y !== arr[k - 1].y);
  const h = hover !== null ? series[hover] : null;
  return (
    <div className="relative" onPointerLeave={() => setHover(null)}>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="h-64 w-full">
        {[0.25, 0.5, 0.75].map((t) => (
          <line key={t} x1={0} x2={W} y1={y(t)} y2={y(t)} stroke="white" strokeOpacity={0.06} vectorEffect="non-scaling-stroke" />
        ))}
        {yearStarts.map((s) => (
          <line key={s.y} x1={x(s.i)} x2={x(s.i)} y1={0} y2={H} stroke="white" strokeOpacity={0.05} vectorEffect="non-scaling-stroke" />
        ))}
        <path d={`${path(model)} L${W},${H} L0,${H} Z`} fill="url(#health-fill)" />
        <defs>
          <linearGradient id="health-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#a531d6" stopOpacity={0.35} />
            <stop offset="100%" stopColor="#a531d6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <path d={path(base)} fill="none" stroke="rgba(255,255,255,0.45)" strokeWidth={1.5} strokeDasharray="5 4" vectorEffect="non-scaling-stroke" />
        <motion.path d={path(model)} fill="none" stroke="#e2a6ff" strokeWidth={2.2} vectorEffect="non-scaling-stroke" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 2 }} />
        {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={0} y2={H} stroke="white" strokeOpacity={0.6} vectorEffect="non-scaling-stroke" />}
      </svg>
      <div className="absolute inset-0 flex">
        {series.map((s, i) => (
          <a key={s.setlist_id} href={`#/analysis/shows/${s.setlist_id}`} className="h-full flex-1" onPointerEnter={() => setHover(i)} aria-label={`Show on ${s.event_date}`} />
        ))}
      </div>
      <div className="relative mt-1 h-4 font-mono text-[10px] text-white/40">
        {yearStarts.map((s) => (
          <span key={s.y} className="absolute -translate-x-1/2" style={{ left: `${(s.i / (series.length - 1)) * 100}%` }}>
            {s.y.slice(2)}
          </span>
        ))}
      </div>
      {h && (
        <div
          className="pointer-events-none absolute top-2 rounded-xl bg-ink/85 px-3 py-2 text-xs ring-1 ring-white/10 backdrop-blur-xl"
          style={{ left: `clamp(0px, calc(${(hover! / (series.length - 1)) * 100}% - 6rem), calc(100% - 12rem))` }}
        >
          <p className="text-white">{h.event_date}</p>
          <p className="text-white/60">model {pct(h.accuracy)}, baseline {pct(h.baseline)}</p>
          <p className="text-white/40">click to open the night</p>
        </div>
      )}
    </div>
  );
}

export default function ModelHealth() {
  const [data, setData] = useState<Health | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    api.modelHealth().then(setData).catch(() => setFailed(true));
  }, []);
  if (failed) return <div className="text-sm text-white/55">The replay is not available. Run: uv run python -m undercurrents.prediction.cli train-models --with-sequence</div>;
  if (!data) return <div className="h-[60vh] animate-pulse rounded-[26px] bg-white/[0.04]" />;

  const years = Object.entries(data.by_year);
  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.synthTable.src} alt={PHOTOS.synthTable.alt} size={56} accent="ember" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">Model Health</h1>
        </div>
        <p className="max-w-md text-sm leading-relaxed text-white/50 sm:text-right">
          The setlist model replayed over {data.shows_scored} shows it had never seen, refitted every {data.refit_every} shows after a {data.warm_up_shows}-show warm-up
        </p>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-3">
        <Card tinted accent="violet">
          <p className="text-[13px] font-medium text-violet-light">Songs called per night</p>
          <p className="mt-3 font-display text-4xl">{pct(data.mean_accuracy)}</p>
          <p className="mt-1 text-sm text-white/55">vs {pct(data.mean_baseline_accuracy)} for "the most played songs so far"</p>
        </Card>
        <Card>
          <p className="text-[13px] font-medium text-white/55">Brier score</p>
          <p className="mt-3 font-display text-4xl">{data.brier_score.toFixed(3)}</p>
          <p className="mt-1 text-sm text-white/55">mean squared gap between probability and outcome, lower is better</p>
        </Card>
        <Card>
          <p className="text-[13px] font-medium text-white/55">How it was tested</p>
          <p className="mt-3 text-sm leading-relaxed text-white/65">
            Each night was predicted from earlier nights only. Accuracy asks the model for as many songs as the night had and counts how many were played.
          </p>
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[1fr_1.4fr]">
        <Card>
          <p className="text-[13px] font-medium text-white/55">Are its probabilities honest?</p>
          <p className="mt-1 text-xs text-white/40">The dashed diagonal is perfect calibration. Circle size: how many predictions fell in the bin.</p>
          <div className="mt-4">
            <Calibration bins={data.calibration} />
          </div>
        </Card>
        <Card>
          <p className="text-[13px] font-medium text-white/55">By year</p>
          <div className="mt-4 space-y-2">
            {years.map(([year, y]) => (
              <div key={year} className="flex items-center gap-3">
                <span className="w-10 font-mono text-xs text-white/50">{year}</span>
                <div className="relative h-4 flex-1 overflow-hidden rounded-full bg-white/[0.05]">
                  <div className="absolute inset-y-0 left-0 rounded-full bg-white/20" style={{ width: pct(y.baseline) }} />
                  <motion.div className="absolute inset-y-1 left-0 rounded-full bg-gradient-to-r from-violet to-violet-light" initial={{ width: 0 }} whileInView={{ width: pct(y.accuracy) }} viewport={{ once: true }} transition={{ duration: 1 }} />
                </div>
                <span className="w-10 text-right font-mono text-xs text-white">{pct(y.accuracy)}</span>
                <span className="hidden w-28 text-right text-[11px] text-white/40 sm:block">{pct(y.new_song_share)} new songs</span>
              </div>
            ))}
          </div>
          <p className="mt-4 text-xs leading-relaxed text-white/45">
            Weakest years: {years.slice().sort((a, b) => a[1].accuracy - b[1].accuracy).slice(0, 2).map(([yr, v]) => `${yr} (${pct(v.accuracy)})`).join(" and ")}. A song played for the first time has no history for the model to rank, so the share of new songs in a year (right column) is the first place to look when accuracy drops.
          </p>
        </Card>
      </div>

      <div className="mt-6">
        <Card>
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <p className="text-[13px] font-medium text-white/55">Accuracy through time, rolling over {ROLL} shows</p>
            <span className="flex gap-4 text-xs text-white/50">
              <span className="flex items-center gap-1.5"><span className="h-0.5 w-4 bg-violet-light" /> model</span>
              <span className="flex items-center gap-1.5"><span className="h-0.5 w-4 border-t border-dashed border-white/60" /> baseline</span>
            </span>
          </div>
          <div className="mt-4">
            <Timeline series={data.series} />
          </div>
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card>
          <p className="text-[13px] font-medium text-white/55">Hardest nights (8 songs or more)</p>
          <ul className="mt-3 space-y-1">
            {data.hardest_nights.map((n) => (
              <li key={n.setlist_id}>
                <a href={`#/analysis/shows/${n.setlist_id}`} className="flex items-center justify-between gap-3 rounded-lg px-2 py-1.5 text-sm hover:bg-white/[0.06]">
                  <span className="font-mono text-xs text-white/60">{n.event_date}</span>
                  <span className="text-white/50">{n.unseen_songs} of {n.played} songs never played before</span>
                  <span className="font-mono text-xs text-ember-light">{pct(n.accuracy)}</span>
                </a>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <p className="text-[13px] font-medium text-white/55">Biggest wins over the baseline</p>
          <ul className="mt-3 space-y-1">
            {data.biggest_wins_over_baseline.map((n) => (
              <li key={n.setlist_id}>
                <a href={`#/analysis/shows/${n.setlist_id}`} className="flex items-center justify-between gap-3 rounded-lg px-2 py-1.5 text-sm hover:bg-white/[0.06]">
                  <span className="font-mono text-xs text-white/60">{n.event_date}</span>
                  <span className="font-mono text-xs text-white/50">{pct(n.baseline)} → <span className="text-violet-light">{pct(n.accuracy)}</span></span>
                </a>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
