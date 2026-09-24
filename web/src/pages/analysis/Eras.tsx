import { motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { Eras as ErasData } from "../../lib/types";
import { ALBUM_COLOURS } from "../../lib/albumColours";

const colourOf = (name: string) => ALBUM_COLOURS[name] ?? "#9d8fb0";

const W = 1000;
const H = 420;

// Monotone cubic (Fritsch-Carlson) through the points: the stream flows between years without
// the overshoot a Catmull-Rom spline would add, so a record never appears to be played in a
// year where its share was zero.
function smooth(points: [number, number][]): string {
  const n = points.length;
  if (n < 2) return "";
  const dx = points.slice(1).map((p, i) => p[0] - points[i][0]);
  const slope = points.slice(1).map((p, i) => (p[1] - points[i][1]) / dx[i]);
  const m = points.map((_, i) => {
    if (i === 0) return slope[0];
    if (i === n - 1) return slope[n - 2];
    return slope[i - 1] * slope[i] <= 0 ? 0 : (slope[i - 1] + slope[i]) / 2;
  });
  for (let i = 0; i < n - 1; i++) {
    if (slope[i] === 0) {
      m[i] = 0;
      m[i + 1] = 0;
      continue;
    }
    const a = m[i] / slope[i];
    const b = m[i + 1] / slope[i];
    const h = a * a + b * b;
    if (h > 9) {
      const t = 3 / Math.sqrt(h);
      m[i] = t * a * slope[i];
      m[i + 1] = t * b * slope[i];
    }
  }
  let d = `M${points[0][0]},${points[0][1]}`;
  for (let i = 0; i < n - 1; i++) {
    const [x0, y0] = points[i];
    const [x1, y1] = points[i + 1];
    const h = (x1 - x0) / 3;
    d += ` C${x0 + h},${y0 + m[i] * h} ${x1 - h},${y1 - m[i + 1] * h} ${x1},${y1}`;
  }
  return d;
}

export default function Eras() {
  const [data, setData] = useState<ErasData | null>(null);
  const [focus, setFocus] = useState<string | null>(null);
  const [hoverYear, setHoverYear] = useState<number | null>(null);

  useEffect(() => {
    api.eras().then(setData).catch(() => {});
  }, []);

  const layers = useMemo(() => {
    if (!data || data.years.length < 2) return [];
    const n = data.years.length;
    // Each year holds its value across most of its own column and changes quickly at the
    // boundary, so a record never appears to be played in the year before its first show.
    const col = W / n;
    const xs = data.years.flatMap((_, i) => [i * col + col * 0.18, (i + 1) * col - col * 0.18]);
    const pad = (arr: number[]) => [arr[0], ...arr, arr[arr.length - 1]];
    const xsPadded = [0, ...xs, W];
    const base = new Array(n).fill(0);
    return data.records.map((rec) => {
      const lowerVals = pad(base.flatMap((b) => [b, b]));
      data.years.forEach((y, i) => (base[i] += y.shares[rec.name] ?? 0));
      const upperVals = pad(base.flatMap((b) => [b, b]));
      const upper = xsPadded.map((x, k) => [x, H - upperVals[k] * H] as [number, number]);
      const lower = xsPadded.map((x, k) => [x, H - lowerVals[k] * H] as [number, number]);
      const path = `${smooth(upper)} L${lower[lower.length - 1][0]},${lower[lower.length - 1][1]} ${smooth([...lower].reverse()).slice(1).replace(/^/, "L")} Z`;
      return { ...rec, path };
    });
  }, [data]);

  const summaries = useMemo(() => {
    if (!data) return [];
    return data.records
      .filter((r) => r.kind === "album")
      .map((r) => {
        const series = data.years.map((y) => ({ year: y.year, share: y.shares[r.name] ?? 0 }));
        const peak = series.reduce((a, b) => (b.share > a.share ? b : a));
        const last = series[series.length - 1];
        return { ...r, peak, last };
      });
  }, [data]);

  if (!data) return <div className="h-[60vh] animate-pulse rounded-[26px] bg-white/[0.04]" />;
  if (data.years.length === 0)
    return <div className="text-sm text-white/55">No album data yet. Run: uv run python -m undercurrents.clustering.albums</div>;

  const n = data.years.length;
  const hovered = hoverYear !== null ? data.years[hoverYear] : null;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.stageRainbowLights.src} alt={PHOTOS.stageRainbowLights.alt} size={56} accent="ember" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">Eras</h1>
        </div>
        <p className="text-sm leading-relaxed text-white/50 sm:text-right">
          Which record the songs came from, year by year
          <br />
          {data.coverage && `${data.coverage.with_album.toLocaleString("en")} of ${data.coverage.performances.toLocaleString("en")} performances matched to a record`}
        </p>
      </div>

      <Card className="mt-10">
        <div className="flex flex-wrap gap-2">
          {data.records.map((r) => (
            <button
              key={r.name}
              type="button"
              onClick={() => setFocus(focus === r.name ? null : r.name)}
              className={`flex items-center gap-2 rounded-full px-3 py-1.5 text-[13px] ring-1 transition-opacity ${focus && focus !== r.name ? "opacity-40 ring-white/5" : "ring-white/15"}`}
            >
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: colourOf(r.name) }} />
              {r.name}
              {r.release_date && <span className="font-mono text-[11px] text-white/40">{r.release_date.slice(0, 4)}</span>}
            </button>
          ))}
        </div>

        <div className="relative mt-6" onPointerLeave={() => setHoverYear(null)}>
          <svg viewBox={`0 0 ${W} ${H}`} className="h-[22rem] w-full sm:h-[26rem]" preserveAspectRatio="none">
            {layers.map((layer, i) => (
              <motion.path
                key={layer.name}
                d={layer.path}
                fill={colourOf(layer.name)}
                initial={{ opacity: 0, scaleY: 0.2 }}
                animate={{ opacity: focus && focus !== layer.name ? 0.12 : 0.92, scaleY: 1 }}
                style={{ transformOrigin: "50% 100%" }}
                transition={{ duration: 0.9, delay: i * 0.05, ease: [0.22, 1, 0.36, 1] }}
              />
            ))}
            {hoverYear !== null && <line x1={((hoverYear + 0.5) / n) * W} x2={((hoverYear + 0.5) / n) * W} y1={0} y2={H} stroke="white" strokeOpacity={0.7} vectorEffect="non-scaling-stroke" />}
          </svg>
          {/* hover strips, one per year */}
          <div className="absolute inset-0 flex">
            {data.years.map((y, i) => (
              <div key={y.year} className="h-full flex-1" onPointerEnter={() => setHoverYear(i)} />
            ))}
          </div>
          {hovered && (
            <div
              className="pointer-events-none absolute top-3 z-10 w-56 rounded-2xl bg-ink/85 p-4 text-sm shadow-2xl ring-1 ring-white/10 backdrop-blur-xl"
              style={{ left: `clamp(0px, calc(${((hoverYear! + 0.5) / n) * 100}% - 7rem), calc(100% - 14rem))` }}
            >
              <p className="font-serif text-xl italic text-white">{hovered.year}</p>
              <p className="text-xs text-white/45">{hovered.performances} songs performed</p>
              <ul className="mt-2 space-y-1">
                {data.records
                  .filter((r) => (hovered.shares[r.name] ?? 0) > 0)
                  .sort((a, b) => (hovered.shares[b.name] ?? 0) - (hovered.shares[a.name] ?? 0))
                  .map((r) => (
                    <li key={r.name} className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full" style={{ background: colourOf(r.name) }} />
                      <span className="min-w-0 flex-1 truncate text-white/80">{r.name}</span>
                      <span className="font-mono text-xs text-white/55">{Math.round((hovered.shares[r.name] ?? 0) * 100)}%</span>
                    </li>
                  ))}
              </ul>
            </div>
          )}
        </div>
        <div className="mt-2 flex font-mono text-[11px] text-white/40">
          {data.years.map((y, i) => (
            <span key={y.year} className={`flex-1 text-center ${i % 2 && n > 12 ? "invisible sm:visible" : ""}`}>{y.year}</span>
          ))}
        </div>
        {data.source && <p className="mt-4 text-xs text-white/40">{data.source}</p>}
      </Card>

      <div className="mt-6 grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-5">
        {summaries.map((s) => (
          <Card key={s.name}>
            <span className="block h-1 w-10 rounded-full" style={{ background: colourOf(s.name) }} />
            <p className="mt-4 font-display text-lg text-white">{s.name}</p>
            <p className="font-mono text-xs text-white/40">released {s.release_date}</p>
            <p className="mt-4 text-sm text-white/65">
              Peak: <span className="text-white">{Math.round(s.peak.share * 100)}%</span> of the set in {s.peak.year}
            </p>
            <p className="text-sm text-white/65">
              In {s.last.year}: <span className="text-white">{Math.round(s.last.share * 100)}%</span>
            </p>
          </Card>
        ))}
      </div>
    </div>
  );
}
