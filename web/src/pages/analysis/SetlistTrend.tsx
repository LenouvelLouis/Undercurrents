import { useEffect, useState } from "react";
import Card from "../../components/Card";
import { api } from "../../lib/api";
import coverCurrents from "../../assets/cover-currents.jpg";
import coverInnerspeaker from "../../assets/cover-innerspeaker.jpg";
import coverLonerism from "../../assets/cover-lonerism.jpg";
import coverSlowRush from "../../assets/cover-slowrush.jpg";
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

  return (
    <div>
      <div className="flex items-start justify-between">
        <h1 className="font-display text-5xl font-bold">
          Setlist
          <br />
          Trend
        </h1>
        <p className="text-right font-mono text-xs italic text-white/40">
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
          </defs>

          {gridValues.map((value) => (
            <g key={value}>
              <line x1={0} y1={y(value)} x2={width} y2={y(value)} stroke="rgba(255,255,255,0.05)" strokeWidth={1} />
              <text x={6} y={y(value) - 4} className="font-mono" fontSize="9" fill="rgba(255,255,255,0.25)">
                {value.toFixed(1)}
              </text>
            </g>
          ))}

          {data.eras.map((era) => {
            const startX = x(Math.max(era.start_year, minYear));
            const endX = x(Math.min(era.end_year, maxYear));
            const cover = ERA_COVERS[era.name];
            return (
              <g key={era.name}>
                <rect x={startX} y={0} width={Math.max(0, endX - startX)} height={height} fill={ERA_TINTS[era.name] ?? "transparent"} />
                {cover && (
                  <image
                    href={cover}
                    x={startX + 8}
                    y={26}
                    width={28}
                    height={28}
                    style={{ clipPath: "inset(0% round 4px)" }}
                    opacity={0.9}
                  />
                )}
                <text x={startX + (cover ? 44 : 8)} y={20} className="font-mono" fontSize="11" fill="rgba(255,255,255,0.4)">
                  {era.name.toUpperCase()}
                </text>
              </g>
            );
          })}

          <polygon points={areaPoints} fill="url(#trend-area)" />
          <polyline points={points} fill="none" stroke="url(#trend-line)" strokeWidth={3} strokeLinejoin="round" />
          {years.map((year, i) => (
            <circle key={year} cx={x(year)} cy={y(values[i])} r={3.5} fill="#0d0710" stroke="url(#trend-line)" strokeWidth={2} />
          ))}
        </svg>
      </Card>
    </div>
  );
}
