import { useEffect, useState } from "react";
import Card from "../../components/Card";
import PhotoPanel from "../../components/PhotoPanel";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { NextDate as NextDateData } from "../../lib/types";

function formatDate(iso: string) {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

const WEEKDAYS = ["S", "M", "T", "W", "T", "F", "S"];

// A small real calendar grid for the predicted date's month, built purely from that one
// ISO date (no extra data invented): it lets the point estimate read as an actual date on
// a calendar rather than only a number line, which is the other real view already shown.
function MonthCalendar({ iso, accent = "#a531d6" }: { iso: string; accent?: string }) {
  const target = new Date(iso + "T00:00:00");
  const year = target.getFullYear();
  const month = target.getMonth();
  const firstWeekday = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const cells: (number | null)[] = [...Array(firstWeekday).fill(null), ...Array.from({ length: daysInMonth }, (_, i) => i + 1)];

  return (
    <div>
      <div className="font-mono text-xs uppercase tracking-widest text-white/40">
        {target.toLocaleDateString("en-US", { month: "long", year: "numeric" })}
      </div>
      <div className="mt-4 grid grid-cols-7 gap-1.5">
        {WEEKDAYS.map((d, i) => (
          <div key={i} className="text-center font-mono text-[10px] text-white/30">
            {d}
          </div>
        ))}
        {cells.map((day, i) => {
          const isTarget = day === target.getDate();
          const cellDate = day ? new Date(year, month, day) : null;
          const isPast = cellDate ? cellDate < today : false;
          return (
            <div
              key={i}
              className={`flex aspect-square items-center justify-center rounded-md font-mono text-xs ${
                day === null
                  ? ""
                  : isTarget
                    ? "font-bold text-ink shadow-glow-violet"
                    : isPast
                      ? "text-white/15"
                      : "text-white/50"
              }`}
              style={isTarget ? { backgroundColor: accent } : undefined}
            >
              {day}
            </div>
          );
        })}
      </div>
    </div>
  );
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
        <h1 className="font-display text-6xl font-bold">
          Next
          <br />
          Date
        </h1>
        <p className="text-right font-mono text-xs italic text-white/40">Predicted date of the next announced show</p>
      </div>
      {data && (
        <div className="mt-10 grid grid-cols-6 gap-6">
          <Card tinted className="anim-fade-in-up col-span-6 lg:col-span-3">
            <div className="font-display text-6xl font-bold">{formatDate(data.predicted_date)}</div>
            <div className="mt-2 font-mono text-sm text-white/50">
              predicted mean: {data.days_from_today} days out
            </div>

            {/* Today -> predicted date timeline, shaded band = mean absolute error */}
            <div className="relative mx-1 mt-12 h-3 rounded-full bg-white/5">
              <div
                className="absolute top-1/2 -translate-y-1/2 rounded-full bg-violet/25"
                style={{ left: `${Math.max(0, markerPct - bandPct)}%`, width: `${bandPct * 2}%`, height: "16px" }}
              />
              <div
                className="anim-width-in h-full rounded-full bg-gradient-to-r from-violet-dark via-violet to-violet-light"
                style={{ width: `${markerPct}%`, animationDelay: "0.3s" }}
              />
              <div className="absolute -top-7 left-0 font-mono text-xs uppercase tracking-widest text-white/40">Today</div>
              <div
                className="absolute -top-9 flex -translate-x-1/2 flex-col items-center"
                style={{ left: `${markerPct}%` }}
              >
                <span className="rounded-full bg-violet px-2.5 py-1 font-mono text-xs font-bold text-ink shadow-glow-violet">
                  {formatDate(data.predicted_date)}
                </span>
                <span className="mt-1 h-4 w-px bg-violet-light" />
              </div>
            </div>
            <div className="mt-8 font-mono text-xs text-white/30">
              shaded band: ± {data.mae_days} days of mean absolute error
            </div>

            <div className="mt-8 flex gap-10">
              <div>
                <div className="font-mono text-xs uppercase tracking-widest text-white/40">Mean abs. error</div>
                <div className="font-display text-2xl font-bold">{data.mae_days} days</div>
              </div>
              <div>
                <div className="font-mono text-xs uppercase tracking-widest text-white/40">Median abs. error</div>
                <div className="font-display text-2xl font-bold">{data.median_absolute_error_days} days</div>
              </div>
            </div>
          </Card>

          <Card className="anim-fade-in-up col-span-6 lg:col-span-2" style={{ animationDelay: "0.15s" }}>
            <MonthCalendar iso={data.predicted_date} />
          </Card>

          <PhotoPanel
            photo={PHOTOS.roundStageAerial}
            accent="violet"
            tag="the stage waiting"
            className="col-span-6 h-[16rem] lg:col-span-1 lg:h-auto"
            focus="center 35%"
            style={{ animationDelay: "0.1s" }}
          />

          <PhotoPanel
            photo={PHOTOS.arenaAerial}
            accent="violet"
            tag="until then, count the days"
            className="col-span-6 h-[20rem] lg:col-span-2"
            focus="center 35%"
            style={{ animationDelay: "0.3s" }}
          />
          <PhotoPanel
            photo={PHOTOS.arenaLasersWide}
            accent="violet"
            className="col-span-6 h-[20rem] lg:col-span-4"
            focus="center 45%"
            style={{ animationDelay: "0.36s" }}
          />
        </div>
      )}
    </div>
  );
}
