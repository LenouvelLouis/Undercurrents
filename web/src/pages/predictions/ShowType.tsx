import { motion } from "motion/react";
import { useEffect, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { ShowFormats, ShowTypePrediction } from "../../lib/types";

const pct = (v: number) => `${Math.round(v * 100)}%`;

export default function ShowType() {
  const [data, setData] = useState<ShowTypePrediction | null>(null);
  const [formats, setFormats] = useState<ShowFormats | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.showType().then(setData).catch(() => setFailed(true));
    api.showFormats().then(setFormats).catch(() => {});
  }, []);

  if (failed)
    return (
      <div className="text-sm text-white/55">
        Show types are not built yet. Run: uv run python -m undercurrents.derived.cli build
      </div>
    );
  if (!data) return <div className="h-[60vh] animate-pulse rounded-[26px] bg-white/[0.04]" />;

  const a = data.accuracy;
  const p = data.probability_festival;
  const maxYear = Math.max(...(formats?.by_year.map((y) => y.festival + y.headline) ?? [1]), 1);
  const beaten = a.methods.find((m) => !m.chosen && m.test_score > (a.methods.find((x) => x.chosen)?.test_score ?? 0));

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.silhouetteLasers.src} alt={PHOTOS.silhouetteLasers.alt} size={56} accent="violet" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">Festival or Headline</h1>
        </div>
        <p className="text-sm leading-relaxed text-white/50 sm:text-right">
          Is the next night a festival slot or their own show?
          <br />
          {a.classified_shows} past shows classified, {pct(a.festival_share)} of them festivals
        </p>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-6 xl:grid-cols-[1fr_1.2fr]">
        <Card tinted accent="violet" className="flex flex-col justify-center">
          <p className="text-[13px] font-medium text-violet-light">Next show, from {data.reference_month}</p>
          <div className="mt-6 flex items-end gap-5">
            <span className="font-hero text-[5.5rem] font-extrabold leading-none">{pct(p)}</span>
            <span className="pb-3 text-lg text-white/60">chance of a festival slot</span>
          </div>
          <div className="mt-6 h-3 overflow-hidden rounded-full bg-white/[0.08]">
            <motion.div className="h-full rounded-full bg-gradient-to-r from-amber to-amber-light" initial={{ width: 0 }} animate={{ width: pct(p) }} transition={{ duration: 1.2, ease: [0.22, 1, 0.36, 1] }} />
          </div>
          <div className="mt-3 flex justify-between text-xs text-white/45">
            <span>festival</span>
            <span>headline</span>
          </div>
          <div className="mt-8 grid grid-cols-3 gap-4 border-t border-white/10 pt-6">
            <div>
              <p className="font-display text-3xl">{data.songs_if_festival ?? "?"}</p>
              <p className="text-xs text-white/50">songs if festival</p>
            </div>
            <div>
              <p className="font-display text-3xl">{data.songs_if_headline ?? "?"}</p>
              <p className="text-xs text-white/50">songs if headline</p>
            </div>
            <div>
              <p className="font-display text-3xl text-violet-light">{data.expected_songs}</p>
              <p className="text-xs text-white/50">songs, weighted</p>
            </div>
          </div>
          <p className="mt-4 text-xs leading-relaxed text-white/40">
            Song counts are the medians of the last 20 shows of each kind. The last show on record ({data.last_show?.date}) was a{" "}
            {data.last_show?.festival ? "festival slot" : "headline show"}.
          </p>
        </Card>

        <Card>
          <p className="text-[13px] font-medium text-white/55">Which method ships, and why</p>
          <p className="mt-2 text-[13px] leading-relaxed text-white/50">
            Three methods, picked on {a.validation_folds} separate stretches of {a.fold_shows} shows, then scored once on the {a.test_shows} latest shows. Score: {a.metric}.
          </p>
          <div className="mt-5 space-y-4">
            {a.methods.map((m) => (
              <div key={m.key}>
                <div className="flex items-baseline justify-between gap-3">
                  <span className={`text-sm ${m.chosen ? "text-cream" : "text-white/55"}`}>
                    {m.name}
                    {m.chosen && <span className="ml-2 text-[11px] text-violet-light">chosen</span>}
                  </span>
                  <span className="font-mono text-xs text-white/50">test {m.test_score.toFixed(3)}</span>
                </div>
                <div className="mt-1.5 flex items-center gap-2">
                  <span className="w-20 shrink-0 text-[11px] text-white/45">validation</span>
                  <div className="relative h-1.5 grow rounded-full bg-white/[0.06]">
                    <div className="h-full rounded-full bg-white/25" style={{ width: `${((m.validation_score - 0.5) / 0.5) * 100}%` }} />
                    {m.fold_scores.map((f, i) => (
                      <span key={i} className="absolute top-1/2 h-2.5 w-px -translate-y-1/2 bg-white/60" style={{ left: `${((f - 0.5) / 0.5) * 100}%` }} />
                    ))}
                  </div>
                  <span className="w-12 text-right font-mono text-[11px] text-white/45">{m.validation_score.toFixed(3)}</span>
                </div>
              </div>
            ))}
          </div>
          <p className="mt-4 text-[13px] leading-relaxed text-white/50">{a.selection.reason}.</p>
          {beaten && (
            <p className="mt-3 border-t border-white/10 pt-3 text-[13px] leading-relaxed text-white/50">
              Worth saying plainly: on the test window "{beaten.name}" scored higher. The latest shows are an arena tour with almost no festivals, which a flat base rate predicts very well. It was not picked, because that would mean choosing on the test set.
            </p>
          )}
        </Card>
      </div>

      {formats && (
        <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[1.3fr_1fr]">
          <Card>
            <p className="text-[13px] font-medium text-white/55">Festival slots per year</p>
            <div className="mt-6 flex h-48 items-stretch gap-2 overflow-x-auto">
              {formats.by_year.map((y) => {
                const total = y.festival + y.headline;
                return (
                  <div key={y.year} className="flex h-full min-w-[26px] flex-1 flex-col items-center justify-end gap-1" title={`${y.year}: ${y.festival} festival, ${y.headline} headline`}>
                    <div className="flex w-full flex-col justify-end overflow-hidden rounded-t-md" style={{ height: `${(total / maxYear) * 100}%` }}>
                      <div className="bg-amber-light/90" style={{ height: `${total ? (y.festival / total) * 100 : 0}%` }} />
                      <div className="flex-1 bg-white/15" />
                    </div>
                    <span className="font-mono text-[10px] text-white/40">{String(y.year).slice(2)}</span>
                  </div>
                );
              })}
            </div>
            <div className="mt-3 flex gap-4 text-xs text-white/50">
              <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-amber-light" /> festival</span>
              <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-white/30" /> headline</span>
            </div>
            <p className="mt-4 text-xs leading-relaxed text-white/40">{formats.method}</p>
          </Card>
          <Card>
            <p className="text-[13px] font-medium text-white/55">Every festival call, with its evidence</p>
            <ul className="mt-3 max-h-80 space-y-3 overflow-y-auto pr-1">
              {formats.festivals.map((f) => (
                <li key={f.setlist_id}>
                  <a href={`#/analysis/shows/${f.setlist_id}`} className="block rounded-lg px-2 py-1 hover:bg-white/[0.05]">
                    <span className="flex items-baseline justify-between gap-3">
                      <span className="truncate text-sm text-white">{f.venue}, {f.city}</span>
                      <span className="shrink-0 font-mono text-[11px] text-white/40">{f.event_date}</span>
                    </span>
                    <span className="block text-xs text-white/45">{f.signals.join(" · ")}</span>
                  </a>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}
    </div>
  );
}
