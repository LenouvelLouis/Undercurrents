import { useEffect, useState } from "react";
import Card from "../../components/Card";
import { api } from "../../lib/api";
import type { SetlistTrend as SetlistTrendData } from "../../lib/types";

const ERA_TINTS: Record<string, string> = {
  Innerspeaker: "rgba(192,38,211,0.10)",
  Lonerism: "rgba(249,115,22,0.10)",
  Currents: "rgba(168,85,247,0.12)",
  "Slow Rush -> Deadbeat": "rgba(45,212,191,0.10)",
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
  const minYear = years[0];
  const maxYear = years[years.length - 1];
  const maxValue = Math.max(...values, 1);
  const x = (year: number) => ((year - minYear) / (maxYear - minYear || 1)) * width;
  const y = (value: number) => height - (value / maxValue) * (height - 40) - 10;
  const points = years.map((year, i) => `${x(year)},${y(values[i])}`).join(" ");

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
          {data.eras.map((era) => {
            const startX = x(Math.max(era.start_year, minYear));
            const endX = x(Math.min(era.end_year, maxYear));
            return (
              <g key={era.name}>
                <rect x={startX} y={0} width={Math.max(0, endX - startX)} height={height} fill={ERA_TINTS[era.name] ?? "transparent"} />
                <text x={startX + 8} y={20} className="font-mono" fontSize="11" fill="rgba(255,255,255,0.4)">
                  {era.name.toUpperCase()}
                </text>
              </g>
            );
          })}
          <polyline points={points} fill="none" stroke="#2dd4bf" strokeWidth={3} />
        </svg>
      </Card>
    </div>
  );
}
