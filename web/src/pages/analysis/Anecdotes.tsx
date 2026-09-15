import { useEffect, useState } from "react";
import { api } from "../../lib/api";
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

  return (
    <div>
      <div className="flex items-start justify-between">
        <h1 className="font-display text-5xl font-bold">Anecdotes</h1>
        <p className="text-right font-mono text-xs italic text-white/40">
          Song debuts, disrupted shows, milestones
          <br />
          newest first
        </p>
      </div>
      <div className="mt-8 max-w-2xl border-l border-white/10 pl-6">
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
              <div className="group relative mb-4 rounded-xl border border-white/5 bg-white/[0.02] p-4 transition-colors hover:border-white/10 hover:bg-white/[0.04]">
                <span className={`absolute -left-[29px] top-6 h-2 w-2 rounded-full ${TAG_DOTS[entry.tag] ?? "bg-white/40"}`} />
                <div className="flex items-center justify-between gap-3">
                  <div className="font-mono text-xs text-white/40">{formatDate(entry.date)}</div>
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest ${TAG_COLORS[entry.tag] ?? "border-white/30 text-white/60"}`}
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
    </div>
  );
}
