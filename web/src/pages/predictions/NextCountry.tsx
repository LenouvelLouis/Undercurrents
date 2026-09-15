import { useEffect, useState } from "react";
import Card from "../../components/Card";
import ProgressBar from "../../components/ProgressBar";
import { api } from "../../lib/api";
import type { CountryPrediction } from "../../lib/types";

export default function NextCountry() {
  const [predictions, setPredictions] = useState<CountryPrediction[]>([]);

  useEffect(() => {
    api.nextCountry().then(setPredictions).catch(() => {});
  }, []);

  const top5 = predictions.slice(0, 5);
  const maxP = Math.max(...top5.map((p) => p.probability), 0.0001);
  const center = 220;

  return (
    <div>
      <div className="flex items-start justify-between">
        <h1 className="font-display text-5xl font-bold">
          Next
          <br />
          Country
        </h1>
        <p className="text-right font-mono text-xs italic text-white/40">
          Ranked probability across {predictions.length} countries played
        </p>
      </div>
      <div className="mt-8 grid grid-cols-2 gap-6">
        <Card className="space-y-4">
          {predictions.slice(0, 8).map((prediction) => (
            <div key={prediction.country}>
              <div className="flex justify-between font-mono text-xs text-white/60">
                <span>{prediction.country}</span>
                <span>{Math.round(prediction.probability * 100)}%</span>
              </div>
              <ProgressBar percentage={prediction.probability * 100} />
            </div>
          ))}
        </Card>

        <Card className="flex items-center justify-center">
          <svg viewBox="0 0 440 440" width="400" height="400">
            {[1, 2, 3].map((ring) => (
              <circle key={ring} cx={center} cy={center} r={(ring / 3) * 150} fill="none" stroke="rgba(255,255,255,0.06)" />
            ))}
            <circle cx={center} cy={center} r={22} fill="rgba(165,49,214,0.18)" stroke="#a531d6" strokeWidth={1.5} />
            <text x={center} y={center + 4} textAnchor="middle" className="font-mono" fontSize="9" fill="rgba(255,255,255,0.7)">
              NEXT SHOW
            </text>
            {top5.map((prediction, i) => {
              const angle = (i / top5.length) * Math.PI * 2 - Math.PI / 2;
              const ringRadius = 55 + (1 - prediction.probability / maxP) * 80;
              const cx = center + Math.cos(angle) * ringRadius;
              const cy = center + Math.sin(angle) * ringRadius;
              const r = 6 + (prediction.probability / maxP) * 16;
              const labelRadius = Math.min(ringRadius + r + 30, center - 30);
              const labelX = center + Math.cos(angle) * labelRadius;
              const labelY = center + Math.sin(angle) * labelRadius;
              return (
                <g key={prediction.country}>
                  <line x1={center} y1={center} x2={cx} y2={cy} stroke="#a531d6" strokeWidth={1} opacity={0.35} />
                  <circle cx={cx} cy={cy} r={r} fill={i === 0 ? "#e2a6ff" : "#a531d6"} opacity={i === 0 ? 1 : 0.75} />
                  <text
                    x={labelX}
                    y={labelY}
                    textAnchor="middle"
                    className="font-mono"
                    fontSize="10"
                    fill="rgba(255,255,255,0.75)"
                  >
                    {prediction.country}
                  </text>
                  <text
                    x={labelX}
                    y={labelY + 13}
                    textAnchor="middle"
                    className="font-mono"
                    fontSize="9"
                    fill="rgba(255,255,255,0.4)"
                  >
                    {Math.round(prediction.probability * 100)}%
                  </text>
                </g>
              );
            })}
          </svg>
        </Card>
      </div>
    </div>
  );
}
