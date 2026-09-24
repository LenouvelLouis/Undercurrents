import { useEffect, useState } from "react";
import Card from "../../components/Card";
import PhotoPanel from "../../components/PhotoPanel";
import { api } from "../../lib/api";
import coverCurrents from "../../assets/cover-currents.jpg";
import coverInnerspeaker from "../../assets/cover-innerspeaker.jpg";
import coverLonerism from "../../assets/cover-lonerism.jpg";
import coverSlowRush from "../../assets/cover-slowrush.jpg";
import { PHOTOS } from "../../lib/photos";
import type { SetlistTrend as SetlistTrendData } from "../../lib/types";

const ERA_TINTS: Record<string, string> = {
  Innerspeaker: "rgba(217,154,63,0.10)",
  Lonerism: "rgba(226,73,47,0.08)",
  Currents: "rgba(165,49,214,0.12)",
  "Slow Rush -> Deadbeat": "rgba(226,73,47,0.12)",
};

const ERA_COVERS: Record<string, string> = {
  Innerspeaker: coverInnerspeaker,
  Lonerism: coverLonerism,
  Currents: coverCurrents,
  "Slow Rush -> Deadbeat": coverSlowRush,
};

export default function SetlistTrend() {
  const [data, setData] = useState<SetlistTrendData | null>(null);

  useEffect(() => {
    api.setlistTrend().then(setData).catch(() => {});
  }, []);

  if (!data) return <p className="font-mono text-xs text-white/30">Loading…</p>;

  const years = Object.keys(data.by_year).map(Number).sort((a, b) => a - b);
  // Real per-era average, derived by averaging the exact same by_year figures the line
  // chart above plots, just grouped into each era's own [start_year, end_year] window
  // rather than invented from scratch.
  const eraAverages = data.eras
    .map((era) => {
      const inRange = years.filter((y) => y >= era.start_year && y <= era.end_year);
      const values = inRange.map((y) => data.by_year[String(y)]);
      const avg = values.length > 0 ? values.reduce((a, b) => a + b, 0) / values.length : null;
      return { ...era, avg, sampleYears: values.length };
    })
    .filter((e) => e.avg !== null);
  const maxEraAvg = Math.max(...eraAverages.map((e) => e.avg ?? 0), 1);
  const values = years.map((year) => data.by_year[String(year)]);
  const width = 1000;
  const height = 360;
  const padTop = 34;
  const padBottom = 28;
  const minYear = years[0];
  const maxYear = years[years.length - 1];
  const maxValue = Math.max(...values, 1);
  const minValue = Math.min(...values, 0);
  const x = (year: number) => ((year - minYear) / (maxYear - minYear || 1)) * width;
  const y = (value: number) =>
    height - padBottom - ((value - minValue) / (maxValue - minValue || 1)) * (height - padTop - padBottom);
  const points = years.map((year, i) => `${x(year)},${y(values[i])}`).join(" ");
  const areaPoints = `0,${height - padBottom} ${points} ${width},${height - padBottom}`;
  const gridValues = Array.from({ length: 4 }, (_, i) => minValue + ((maxValue - minValue) * i) / 3);
  const plotHeight = height - padTop - padBottom;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">
          Setlist Trend
        </h1>
        <p className="text-sm leading-relaxed text-white/50 sm:text-right">
          Average songs per concert
          <br />
          {minYear} → {maxYear}
        </p>
      </div>
      <Card className="mt-8 overflow-hidden p-0">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
          <defs>
            <linearGradient id="trend-line" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2={width} y2="0">
              <stop offset="0%" stopColor="#a531d6" />
              <stop offset="100%" stopColor="#e2492f" />
            </linearGradient>
            <linearGradient id="trend-area" gradientUnits="userSpaceOnUse" x1="0" y1={padTop} x2="0" y2={height - padBottom}>
              <stop offset="0%" stopColor="#e2492f" stopOpacity={0.28} />
              <stop offset="100%" stopColor="#e2492f" stopOpacity={0} />
            </linearGradient>
            {/* Vertical vignette used to fade album art into the background on both edges,
                so covers read as an atmospheric backdrop rather than pasted-on thumbnails. */}
            <linearGradient id="cover-fade-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="white" stopOpacity={0} />
              <stop offset="30%" stopColor="white" stopOpacity={0.6} />
              <stop offset="70%" stopColor="white" stopOpacity={0.6} />
              <stop offset="100%" stopColor="white" stopOpacity={0} />
            </linearGradient>
            <mask id="cover-fade-mask" maskContentUnits="objectBoundingBox">
              <rect x={0} y={0} width={1} height={1} fill="url(#cover-fade-grad)" />
            </mask>
          </defs>

          {gridValues.map((value) => (
            <g key={value}>
              <line x1={0} y1={y(value)} x2={width} y2={y(value)} stroke="rgba(255,255,255,0.05)" strokeWidth={1} />
              <text x={6} y={y(value) - 4} className="font-mono" fontSize="9" fill="rgba(255,255,255,0.25)">
                {value.toFixed(1)}
              </text>
            </g>
          ))}

          {data.eras.map((era, i) => {
            const startX = x(Math.max(era.start_year, minYear));
            const endX = x(Math.min(era.end_year, maxYear));
            const bandWidth = Math.max(0, endX - startX);
            const cover = ERA_COVERS[era.name];
            const coverSize = Math.max(56, Math.min(190, bandWidth * 0.82, plotHeight - 16));
            const coverX = startX + bandWidth / 2 - coverSize / 2;
            const coverY = padTop + plotHeight / 2 - coverSize / 2;
            return (
              <g key={era.name} className="trend-era-fade" style={{ animationDelay: `${i * 0.12}s` }}>
                <rect x={startX} y={0} width={bandWidth} height={height} fill={ERA_TINTS[era.name] ?? "transparent"} />
                {cover && (
                  <image
                    href={cover}
                    x={coverX}
                    y={coverY}
                    width={coverSize}
                    height={coverSize}
                    mask="url(#cover-fade-mask)"
                    opacity={0.85}
                    style={{ filter: "saturate(0.75)" }}
                    className="trend-cover-fade"
                    // covers fade in slightly after their era band does
                    // (delay layered on top of the animation's own timing)
                  />
                )}
                <text x={startX + 8} y={20} className="font-mono" fontSize="11" fill="rgba(255,255,255,0.45)">
                  {era.name.toUpperCase()}
                </text>
                <text x={startX + 8} y={height - 10} className="font-mono" fontSize="9" fill="rgba(255,255,255,0.25)">
                  {era.start_year}–{era.end_year}
                </text>
              </g>
            );
          })}

          <polygon points={areaPoints} fill="url(#trend-area)" className="trend-area-fade" />
          <polyline
            points={points}
            fill="none"
            stroke="url(#trend-line)"
            strokeWidth={3}
            strokeLinejoin="round"
            strokeLinecap="round"
            className="trend-line-draw"
          />
          {years.map((year, i) => (
            <circle
              key={year}
              cx={x(year)}
              cy={y(values[i])}
              r={3.5}
              fill="#0d0710"
              stroke="url(#trend-line)"
              strokeWidth={2}
              className="trend-dot-pop"
              style={{ animationDelay: `${1.6 + i * 0.06}s` }}
            />
          ))}
        </svg>
      </Card>

      <Card className="anim-fade-in-up mt-6">
        <div className="text-[13px] font-medium text-white/55">Average songs per era</div>
        <div className="mt-6 flex items-end gap-3 overflow-x-auto sm:gap-6" style={{ height: 180 }}>
          {eraAverages.map((era, i) => {
            const heightPct = Math.max(6, ((era.avg ?? 0) / maxEraAvg) * 100);
            const cover = ERA_COVERS[era.name];
            return (
              <div key={era.name} className="anim-bar-in flex flex-1 flex-col items-center justify-end gap-2" style={{ animationDelay: `${i * 0.08}s` }}>
                <span className="font-display text-lg font-bold">{era.avg?.toFixed(1)}</span>
                <div
                  className="w-full max-w-16 rounded-t-lg bg-gradient-to-t from-ember-dark via-ember to-ember-light"
                  style={{ height: `${heightPct}%` }}
                />
                <div className="flex items-center gap-1.5">
                  {cover && <img src={cover} alt="" className="h-4 w-4 rounded-sm object-cover grayscale" />}
                  <span className="text-[13px] font-medium text-center text-white/55">{era.name}</span>
                </div>
              </div>
            );
          })}
        </div>
      </Card>

      <div className="mt-6 grid grid-cols-3 gap-6">
        <PhotoPanel
          photo={PHOTOS.synthTable}
          accent="ember"
          tag="the rig behind the curve"
          className="col-span-3 h-[20rem] lg:col-span-1"
          focus="center 30%"
        />
        <PhotoPanel
          photo={PHOTOS.arenaLasersWide}
          accent="ember"
          className="col-span-3 h-[20rem] lg:col-span-2"
          focus="center 40%"
          style={{ animationDelay: "0.08s" }}
        />
      </div>
    </div>
  );
}
