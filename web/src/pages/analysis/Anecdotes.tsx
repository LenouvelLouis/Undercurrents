import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { Anecdote } from "../../lib/types";

const TAG_COLORS: Record<string, string> = {
  "song debut": "border-magenta text-magenta-light",
  "disrupted show": "border-orange-500 text-orange-400",
  milestone: "border-teal text-teal-light",
};

function formatDate(iso: string) {
  return new Date(iso + "T00:00:00").toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" });
}

export default function Anecdotes() {
  const [entries, setEntries] = useState<Anecdote[]>([]);

  useEffect(() => {
    api.anecdotes().then(setEntries).catch(() => {});
  }, []);

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
        {entries.map((entry, i) => (
          <div key={i} className="relative mb-8 last:mb-0">
            <span className="absolute -left-[31px] top-1 h-2 w-2 rounded-full bg-white/40" />
            <div className="font-mono text-xs text-white/40">{formatDate(entry.date)}</div>
            <span className={`mt-1 inline-block rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-widest ${TAG_COLORS[entry.tag] ?? "border-white/30 text-white/60"}`}>
              {entry.tag}
            </span>
            <p className="mt-2 text-sm text-white/80">{entry.description}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
