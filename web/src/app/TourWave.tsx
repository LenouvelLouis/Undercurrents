import { motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import type { CalendarHeatmap } from "../lib/types";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// Eighteen years of touring drawn as an audio file: one mirrored bar per month, height = shows
// played that month (real counts from the archive). Quiet stretches between albums read as the
// silence between tracks. A playhead sweeps across; hovering a bar reads out its month.
export default function TourWave() {
  const [data, setData] = useState<CalendarHeatmap | null>(null);
  const [hover, setHover] = useState<number | null>(null);

  useEffect(() => {
    api.heatmapCalendar().then(setData).catch(() => {});
  }, []);

  const bars = useMemo(() => {
    if (!data || data.years.length === 0) return [];
    const byKey = new Map(data.cells.map((c) => [`${c.year}-${c.month}`, c.shows]));
    const out: { year: number; month: number; shows: number }[] = [];
    for (let y = Math.min(...data.years); y <= Math.max(...data.years); y++)
      for (let m = 1; m <= 12; m++) out.push({ year: y, month: m, shows: byKey.get(`${y}-${m}`) ?? 0 });
    return out;
  }, [data]);

  if (bars.length === 0) return <div className="h-40" />;
  const max = Math.max(...bars.map((b) => b.shows), 1);
  const peak = bars.reduce((a, b) => (b.shows > a.shows ? b : a));
  const shown = hover !== null ? bars[hover] : null;

  return (
    <figure>
      <div className="relative h-40 sm:h-52" onPointerLeave={() => setHover(null)}>
        <div className="absolute inset-0 flex items-center gap-[2px]">
          {bars.map((b, i) => {
            const hPct = b.shows === 0 ? 1.5 : 6 + (b.shows / max) * 94;
            const hue = i / bars.length;
            return (
              <motion.span
                key={`${b.year}-${b.month}`}
                onPointerEnter={() => setHover(i)}
                className="relative flex-1 rounded-full"
                style={{
                  background: `linear-gradient(180deg, hsl(${285 - hue * 280} 85% 72%), hsl(${300 - hue * 290} 80% 55%))`,
                  opacity: hover === null || hover === i ? 1 : 0.35,
                }}
                initial={{ height: "1.5%" }}
                whileInView={{ height: `${hPct}%` }}
                viewport={{ once: true }}
                transition={{ duration: 0.9, delay: i * 0.004, ease: [0.22, 1, 0.36, 1] }}
              />
            );
          })}
        </div>
        <span className="tour-playhead pointer-events-none absolute inset-y-0 w-px bg-white/80 shadow-[0_0_12px_2px_rgba(255,255,255,0.6)]" />
      </div>
      <figcaption className="mt-4 flex flex-wrap items-baseline justify-between gap-2 text-sm text-white/50">
        <span>
          {shown ? (
            <>
              <span className="text-white">{MONTHS[shown.month - 1]} {shown.year}</span>, {shown.shows} show{shown.shows === 1 ? "" : "s"}
            </>
          ) : (
            <>Shows per month, {bars[0].year} to {bars[bars.length - 1].year}. Hover to read a month.</>
          )}
        </span>
        <span className="font-mono text-xs">
          busiest: {MONTHS[peak.month - 1]} {peak.year}, {peak.shows} shows
        </span>
      </figcaption>
    </figure>
  );
}
