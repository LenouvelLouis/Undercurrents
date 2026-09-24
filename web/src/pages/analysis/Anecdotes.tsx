import { useEffect, useState } from "react";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { Anecdote } from "../../lib/types";

const TAG_COLORS: Record<string, string> = {
  "song debut": "border-violet text-violet-light",
  "disrupted show": "border-amber text-amber-light",
  milestone: "border-ember text-ember-light",
};

const TAG_DOTS: Record<string, string> = {
  "song debut": "bg-violet",
  "disrupted show": "bg-amber",
  milestone: "bg-ember",
};

function formatDate(iso: string) {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" });
}

function yearOf(iso: string) {
  return new Date(iso + "T00:00:00").getFullYear();
}

export default function Anecdotes() {
  const [entries, setEntries] = useState<Anecdote[]>([]);

  useEffect(() => {
    api.anecdotes().then(setEntries).catch(() => {});
  }, []);

  const years = entries.map((entry) => yearOf(entry.date));
  const yearBoundaries = years.map((year, i) => i === 0 || year !== years[i - 1]);

  // Real counts per tag, aggregated from the same entries the timeline below renders.
  const tagCounts = entries.reduce<Record<string, number>>((acc, e) => {
    acc[e.tag] = (acc[e.tag] ?? 0) + 1;
    return acc;
  }, {});
  const tagList = Object.entries(tagCounts).sort((a, b) => b[1] - a[1]);
  const maxTagCount = Math.max(...tagList.map(([, count]) => count), 1);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.artistRedSeats.src} alt={PHOTOS.artistRedSeats.alt} size={56} accent="ember" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">Anecdotes</h1>
        </div>
        <p className="text-sm leading-relaxed text-white/50 sm:text-right">
          Song debuts, disrupted shows, milestones
          <br />
          newest first
        </p>
      </div>

      {tagList.length > 0 && (
        <div className="mt-8 flex flex-wrap gap-6">
          {tagList.map(([tag, count], i) => (
            <div key={tag} className="anim-fade-in-up min-w-[160px] flex-1" style={{ animationDelay: `${i * 0.05}s` }}>
              <div className="flex items-center justify-between font-mono text-xs text-white/50">
                <span className="flex items-center gap-1.5">
                  <span className={`h-2 w-2 rounded-full ${TAG_DOTS[tag] ?? "bg-white/40"}`} />
                  {tag}
                </span>
                <span>{count}</span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/5">
                <div
                  className="anim-width-in h-full rounded-full bg-gradient-to-r from-ember-dark via-ember to-ember-light"
                  style={{ width: `${(count / maxTagCount) * 100}%`, animationDelay: `${0.1 + i * 0.04}s` }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-8 grid grid-cols-3 gap-8">
        <div className="col-span-3 border-l border-white/10 pl-6 lg:col-span-2">
        {entries.map((entry, i) => {
          const year = years[i];
          const showYear = yearBoundaries[i];
          return (
            <div key={i}>
              {showYear && (
                <div className="relative -ml-6 mb-4 mt-8 flex items-center gap-3 pl-0 first:mt-0">
                  <span className="absolute -left-[35px] h-2.5 w-2.5 rounded-full border-2 border-ember bg-ink" />
                  <span className="font-display text-2xl font-bold text-white/30">{year}</span>
                  <span className="h-px flex-1 bg-white/10" />
                </div>
              )}
              <div
                className="anim-fade-in-up group relative mb-4 rounded-xl border border-white/5 bg-white/[0.02] p-4 transition-colors hover:border-white/10 hover:bg-white/[0.04]"
                style={{ animationDelay: `${(i % 8) * 0.05}s` }}
              >
                <span className={`absolute -left-[29px] top-6 h-2 w-2 rounded-full ${TAG_DOTS[entry.tag] ?? "bg-white/40"}`} />
                <div className="flex items-center justify-between gap-3">
                  <div className="font-mono text-xs text-white/40">{formatDate(entry.date)}</div>
                  <span
                    className={`text-[13px] font-medium inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 ${TAG_COLORS[entry.tag] ??"border-white/30 text-white/60"}`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${TAG_DOTS[entry.tag] ?? "bg-white/40"}`} />
                    {entry.tag}
                  </span>
                </div>
                <p className="mt-2 text-sm text-white/80">{entry.description}</p>
              </div>
            </div>
          );
        })}
        </div>

        <div className="col-span-3 flex flex-col gap-6 lg:col-span-1">
          <PhotoPanel
            photo={PHOTOS.artistRedSeats}
            accent="ember"
            tag="off stage"
            className="h-[15rem]"
            focus="center 40%"
          />
          <PhotoPanel
            photo={PHOTOS.backyardPortrait}
            accent="ember"
            className="h-[22rem]"
            focus="center 25%"
            style={{ animationDelay: "0.08s" }}
          />
          <PhotoPanel
            photo={PHOTOS.stageRainbowLights}
            accent="ember"
            className="h-[18rem]"
            focus="center 35%"
            style={{ animationDelay: "0.16s" }}
          />
        </div>
      </div>
    </div>
  );
}
