import { useEffect, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import ProgressBar from "../../components/ProgressBar";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
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
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.singerConfetti.src} alt={PHOTOS.singerConfetti.alt} size={56} accent="violet" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">
            Next Country
          </h1>
        </div>
        <p className="text-sm leading-relaxed text-white/50 sm:text-right">
          Ranked probability across {predictions.length} countries played
        </p>
      </div>
      <div className="mt-10 grid grid-cols-2 gap-6">
        <Card className="anim-fade-in-up max-h-[640px] space-y-5 overflow-y-auto pr-1">
          {predictions.map((prediction, i) => (
            <div key={prediction.country} className="anim-fade-in-up" style={{ animationDelay: `${i * 0.05}s` }}>
              <div className="flex justify-between font-mono text-sm text-white/60">
                <span>{prediction.country}</span>
                <span>{Math.round(prediction.probability * 100)}%</span>
              </div>
              <ProgressBar percentage={prediction.probability * 100} />
            </div>
          ))}
        </Card>

        <Card className="anim-fade-in-up flex items-center justify-center" style={{ animationDelay: "0.1s" }}>
          <svg viewBox="0 0 440 440" className="w-full max-w-[640px]">
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
                <g key={prediction.country} className="anim-pop-in" style={{ animationDelay: `${0.2 + i * 0.1}s` }}>
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
      <div className="mt-6 grid grid-cols-3 gap-6">
        <PhotoPanel
          photo={PHOTOS.singerConfetti}
          accent="violet"
          tag="wherever it lands next"
          className="col-span-3 h-[19rem] lg:col-span-2"
          focus="center 45%"
          style={{ animationDelay: "0.25s" }}
        />
        <PhotoPanel
          photo={PHOTOS.roundStageOverhead}
          accent="violet"
          className="col-span-3 h-[19rem] lg:col-span-1"
          focus="center 30%"
          style={{ animationDelay: "0.32s" }}
        />
      </div>
    </div>
  );
}
