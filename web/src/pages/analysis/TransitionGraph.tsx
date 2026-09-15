import { useEffect, useState } from "react";
import Card from "../../components/Card";
import { api } from "../../lib/api";
import type { Song, Transitions } from "../../lib/types";

export default function TransitionGraph() {
  const [songs, setSongs] = useState<Song[]>([]);
  const [selected, setSelected] = useState<Song | null>(null);
  const [transitions, setTransitions] = useState<Transitions | null>(null);

  useEffect(() => {
    api.songs().then((data) => {
      setSongs(data);
      const elephant = data.find((s) => s.name === "Elephant");
      setSelected(elephant ?? data[0] ?? null);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (selected) {
      api.transitions(selected.id).then(setTransitions).catch(() => {});
    }
  }, [selected]);

  const topFollowOns = transitions?.follow_ons.slice(0, 3) ?? [];
  const maxP = Math.max(...(transitions?.follow_ons.map((f) => f.probability) ?? []), 0.0001);

  return (
    <div>
      <div className="flex items-start justify-between">
        <h1 className="font-display text-5xl font-bold">
          Transition
          <br />
          Graph
        </h1>
        <p className="text-right font-mono text-xs italic text-white/40">
          What follows a given song
          <br />
          line weight = transition probability
        </p>
      </div>
      <div className="mt-8 grid grid-cols-2 gap-6">
        <Card className="flex items-center justify-center overflow-hidden">
          <svg viewBox="0 0 480 300" width="440" height="300">
            <defs>
              <filter id="source-glow" x="-150%" y="-150%" width="400%" height="400%">
                <feGaussianBlur stdDeviation="8" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
            {topFollowOns.map((follow, i) => {
              const sourceX = 70;
              const sourceY = 220;
              const targetX = 260;
              const targetY = 50 + i * 90;
              const c1x = sourceX + (targetX - sourceX) * 0.55;
              const c1y = sourceY;
              const c2x = sourceX + (targetX - sourceX) * 0.45;
              const c2y = targetY;
              return (
                <g key={follow.song_id}>
                  <path
                    d={`M ${sourceX} ${sourceY} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${targetX} ${targetY}`}
                    fill="none"
                    stroke="#e2492f"
                    strokeWidth={1 + (follow.probability / maxP) * 7}
                    opacity={0.55}
                    strokeLinecap="round"
                  />
                  <circle cx={targetX} cy={targetY} r={5 + (follow.probability / maxP) * 4} fill="#ff9270" />
                  <text x={targetX + 12} y={targetY + 4} className="font-mono" fontSize="11" fill="white">
                    {follow.song_name}
                  </text>
                  <text x={targetX + 12} y={targetY + 17} className="font-mono" fontSize="9" fill="rgba(255,255,255,0.4)">
                    {Math.round(follow.probability * 100)}%
                  </text>
                </g>
              );
            })}
            <circle cx={70} cy={220} r={12} fill="#e2492f" filter="url(#source-glow)" />
            <text x={70} y={252} textAnchor="middle" className="font-mono" fontSize="12" fontWeight={700} fill="white">
              {selected?.name}
            </text>
            <text x={70} y={266} textAnchor="middle" className="font-mono" fontSize="9" fill="rgba(255,255,255,0.4)">
              SOURCE SONG
            </text>
          </svg>
        </Card>
        <Card>
          <select
            value={selected?.id ?? ""}
            onChange={(e) => setSelected(songs.find((s) => s.id === Number(e.target.value)) ?? null)}
            className="w-full rounded-lg border border-white/20 bg-white/5 px-4 py-2 text-white focus:border-ember"
          >
            {songs.map((song) => (
              <option key={song.id} value={song.id}>{song.name}</option>
            ))}
          </select>
          <div className="mt-5 font-mono text-xs uppercase tracking-widest text-white/40">Ranked follow-ons</div>
          <div className="mt-3 space-y-3">
            {transitions?.follow_ons.map((follow, i) => (
              <div key={follow.song_id} className="flex items-center gap-3">
                <span className="w-5 shrink-0 font-mono text-[11px] text-white/30">{String(i + 1).padStart(2, "0")}</span>
                <span className="w-32 shrink-0 truncate font-display text-sm font-medium sm:w-40">{follow.song_name}</span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-ember-dark via-ember to-ember-light"
                    style={{ width: `${Math.max(4, (follow.probability / maxP) * 100)}%` }}
                  />
                </div>
                <span className="w-9 shrink-0 text-right font-mono text-xs text-white/50">
                  {Math.round(follow.probability * 100)}%
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
