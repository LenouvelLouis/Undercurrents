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
        <Card className="flex items-center justify-center">
          <svg viewBox="0 0 400 300" width="400" height="300">
            <circle cx={80} cy={260} r={8} fill="#2dd4bf" />
            <text x={80} y={285} textAnchor="middle" className="font-mono" fontSize="11" fill="white">
              {selected?.name}
            </text>
            {topFollowOns.map((follow, i) => {
              const targetX = 320;
              const targetY = 60 + i * 90;
              return (
                <g key={follow.song_id}>
                  <line x1={80} y1={260} x2={targetX} y2={targetY} stroke="#2dd4bf" strokeWidth={1 + follow.probability * 8} opacity={0.6} />
                  <circle cx={targetX} cy={targetY} r={6} fill="#2dd4bf" />
                  <text x={targetX + 10} y={targetY + 4} className="font-mono" fontSize="11" fill="white">
                    {follow.song_name} {Math.round(follow.probability * 100)}%
                  </text>
                </g>
              );
            })}
          </svg>
        </Card>
        <Card>
          <select
            value={selected?.id ?? ""}
            onChange={(e) => setSelected(songs.find((s) => s.id === Number(e.target.value)) ?? null)}
            className="w-full rounded-lg border border-white/20 bg-white/5 px-4 py-2 text-white"
          >
            {songs.map((song) => (
              <option key={song.id} value={song.id}>{song.name}</option>
            ))}
          </select>
          <div className="mt-4 font-mono text-xs uppercase tracking-widest text-white/40">Ranked follow-ons</div>
          <ul className="mt-2 space-y-2">
            {transitions?.follow_ons.map((follow) => (
              <li key={follow.song_id} className="flex justify-between">
                <span>{follow.song_name}</span>
                <span className="text-white/50">{Math.round(follow.probability * 100)}%</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
