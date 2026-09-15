import { useEffect, useState } from "react";
import Card from "../../components/Card";
import { api } from "../../lib/api";
import type { SetlistLength } from "../../lib/types";

const SCALE_MAX = 30;
const TICKS = [0, 5, 10, 15, 20, 25, 30];

export default function ConcertLength() {
  const [length, setLength] = useState<SetlistLength | null>(null);

  useEffect(() => {
    api.setlistLength().then(setLength).catch(() => {});
  }, []);

  const predicted = length?.predicted_songs ?? null;
  const markerPct = predicted !== null ? Math.min(100, (predicted / SCALE_MAX) * 100) : 0;

  return (
    <div>
      <div className="flex items-start justify-between">
        <h1 className="font-display text-5xl font-bold">
          Concert
          <br />
          Length
        </h1>
        <p className="text-right font-mono text-xs italic text-white/40">
          Predicted song count for the next show
        </p>
      </div>

      <div className="mt-8 grid grid-cols-5 gap-6">
        <Card tinted className="relative col-span-5 flex flex-col items-center justify-center overflow-hidden py-14 text-center lg:col-span-2">
          <div className="pointer-events-none absolute -bottom-20 left-1/2 h-56 w-56 -translate-x-1/2 rounded-full bg-violet/25 blur-3xl" />
          <span className="relative font-display text-8xl font-bold">{predicted ?? "—"}</span>
          <span className="relative mt-2 font-mono text-xs uppercase tracking-widest text-white/50">songs (mean)</span>
        </Card>

        <Card className="col-span-5 flex flex-col justify-center lg:col-span-3">
          <div className="font-mono text-xs uppercase tracking-widest text-white/40">Where it lands on the scale</div>
          <div className="relative mt-10 h-2 rounded-full bg-white/5">
            <div
              className="h-full rounded-full bg-gradient-to-r from-violet-dark via-violet to-violet-light transition-all"
              style={{ width: `${markerPct}%` }}
            />
            {predicted !== null && (
              <div
                className="absolute -top-3 flex -translate-x-1/2 flex-col items-center"
                style={{ left: `${markerPct}%` }}
              >
                <span className="rounded-full bg-violet px-2 py-0.5 font-mono text-[10px] font-bold text-ink shadow-glow-violet">
                  {predicted}
                </span>
                <span className="mt-1 h-3 w-px bg-violet-light" />
              </div>
            )}
          </div>
          <div className="mt-6 flex justify-between font-mono text-[10px] text-white/30">
            {TICKS.map((tick) => (
              <span key={tick} className="flex flex-col items-center gap-1">
                <span className="h-1.5 w-px bg-white/15" />
                {tick}
              </span>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
