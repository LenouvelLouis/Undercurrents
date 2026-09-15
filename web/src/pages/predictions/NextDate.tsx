import { useEffect, useState } from "react";
import Card from "../../components/Card";
import { api } from "../../lib/api";
import artistPhoto from "../../assets/artist-photo.jpg";
import type { NextDate as NextDateData } from "../../lib/types";

function formatDate(iso: string) {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function NextDate() {
  const [data, setData] = useState<NextDateData | null>(null);

  useEffect(() => {
    api.nextDate().then(setData).catch(() => {});
  }, []);

  const scaleEnd = data ? Math.max(data.days_from_today + data.mae_days * 1.5, 14) : 14;
  const markerPct = data ? Math.min(96, (data.days_from_today / scaleEnd) * 100) : 0;
  const bandPct = data ? Math.min(48, (data.mae_days / scaleEnd) * 100) : 0;

  return (
    <div>
      <div className="flex items-start justify-between">
        <h1 className="font-display text-5xl font-bold">
          Next
          <br />
          Date
        </h1>
        <p className="text-right font-mono text-xs italic text-white/40">Predicted date of the next announced show</p>
      </div>
      {data && (
        <div className="mt-8 grid grid-cols-2 gap-6">
          <Card tinted>
            <div className="font-display text-5xl font-bold">{formatDate(data.predicted_date)}</div>
            <div className="mt-2 font-mono text-xs text-white/50">
              predicted mean — {data.days_from_today} days out
            </div>

            {/* Today -> predicted date timeline, shaded band = mean absolute error */}
            <div className="relative mx-1 mt-10 h-2 rounded-full bg-white/5">
              <div
                className="absolute top-1/2 -translate-y-1/2 rounded-full bg-violet/25"
                style={{ left: `${Math.max(0, markerPct - bandPct)}%`, width: `${bandPct * 2}%`, height: "10px" }}
              />
              <div
                className="h-full rounded-full bg-gradient-to-r from-violet-dark via-violet to-violet-light"
                style={{ width: `${markerPct}%` }}
              />
              <div className="absolute -top-6 left-0 font-mono text-[10px] uppercase tracking-widest text-white/40">Today</div>
              <div
                className="absolute -top-8 flex -translate-x-1/2 flex-col items-center"
                style={{ left: `${markerPct}%` }}
              >
                <span className="rounded-full bg-violet px-2 py-0.5 font-mono text-[10px] font-bold text-ink shadow-glow-violet">
                  {formatDate(data.predicted_date)}
                </span>
                <span className="mt-1 h-3 w-px bg-violet-light" />
              </div>
            </div>
            <div className="mt-6 font-mono text-[10px] text-white/30">
              shaded band — ± {data.mae_days} days of mean absolute error
            </div>

            <div className="mt-6 flex gap-8">
              <div>
                <div className="font-mono text-xs uppercase tracking-widest text-white/40">Mean abs. error</div>
                <div className="font-display text-xl font-bold">{data.mae_days} days</div>
              </div>
              <div>
                <div className="font-mono text-xs uppercase tracking-widest text-white/40">Median abs. error</div>
                <div className="font-display text-xl font-bold">{data.median_absolute_error_days} days</div>
              </div>
            </div>
          </Card>
          <div className="relative overflow-hidden rounded-2xl border border-white/10">
            <img src={artistPhoto} alt="Tame Impala live" className="h-full w-full object-cover grayscale contrast-125" />
            <div className="absolute inset-0 bg-gradient-to-t from-ink via-ember-dark/30 to-transparent mix-blend-color" />
            <div className="absolute inset-0 bg-gradient-to-t from-ink/80 via-transparent to-transparent" />
            <div className="grain-overlay" />
            <p className="absolute bottom-4 left-4 font-mono text-[10px] uppercase tracking-widest text-white/60">
              until then — count the days
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
