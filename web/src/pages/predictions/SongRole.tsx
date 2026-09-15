import { useEffect, useState } from "react";
import Card from "../../components/Card";
import ProgressBar from "../../components/ProgressBar";
import { api } from "../../lib/api";
import type { Song, SongRole as SongRoleData } from "../../lib/types";

const STAGE_ORDER: { key: keyof SongRoleData["probabilities"]; label: string }[] = [
  { key: "opener", label: "Opener" },
  { key: "mid", label: "Mid-set" },
  { key: "closer", label: "Closer" },
  { key: "encore", label: "Encore" },
];

export default function SongRole() {
  const [songs, setSongs] = useState<Song[]>([]);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Song | null>(null);
  const [role, setRole] = useState<SongRoleData | null>(null);

  useEffect(() => {
    api.songs().then(setSongs).catch(() => {});
  }, []);

  useEffect(() => {
    if (selected) {
      api.songRole(selected.id).then(setRole).catch(() => {});
    }
  }, [selected]);

  const matches = query.length > 0 ? songs.filter((s) => s.name.toLowerCase().includes(query.toLowerCase())).slice(0, 8) : [];

  return (
    <div className="mx-auto max-w-2xl text-center">
      <h1 className="font-display text-5xl font-bold">Song Role</h1>
      <p className="mt-2 font-mono text-xs italic text-white/40">Where in the set does a given song tend to land?</p>

      <div className="relative mt-8">
        <input
          value={selected ? selected.name : query}
          onChange={(e) => {
            setSelected(null);
            setRole(null);
            setQuery(e.target.value);
          }}
          placeholder="Search a song…"
          className="w-full rounded-full border border-white/20 bg-white/5 px-5 py-3 text-center text-white outline-none focus:border-violet"
        />
        {matches.length > 0 && !selected && (
          <ul className="absolute z-10 mt-2 w-full rounded-lg border border-white/10 bg-bg text-left shadow-xl">
            {matches.map((song) => (
              <li
                key={song.id}
                className="cursor-pointer px-4 py-2 hover:bg-white/10"
                onClick={() => {
                  setSelected(song);
                  setQuery("");
                }}
              >
                {song.name}
              </li>
            ))}
          </ul>
        )}
      </div>

      {!role && (
        <div className="mt-12 flex flex-col items-center gap-4 text-white/30">
          <div className="h-24 w-24 rounded-full border-2 border-dashed border-white/20" />
          <p className="font-mono text-xs">Pick a song to see its role distribution</p>
        </div>
      )}

      {role && (
        <Card className="mt-8 text-left">
          <h2 className="text-center font-display text-xl font-bold">{role.song_name}</h2>

          {/* Horizontal stage-position timeline — dot size/glow scale with probability */}
          <div className="relative mx-2 mt-10 mb-2">
            <div className="absolute left-0 right-0 top-4 h-px bg-white/10" />
            <div className="flex items-start justify-between">
              {STAGE_ORDER.map(({ key, label }) => {
                const p = role.probabilities[key];
                const size = 14 + p * 36;
                return (
                  <div key={key} className="flex w-1/4 flex-col items-center">
                    <span className="mb-1 font-mono text-[11px] text-white/50">{Math.round(p * 100)}%</span>
                    <div
                      className="rounded-full bg-gradient-to-br from-violet-light to-violet shadow-glow-violet"
                      style={{ width: size, height: size }}
                    />
                    <span className="mt-3 font-mono text-[10px] uppercase tracking-widest text-white/40">{label}</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-8 space-y-3">
            {STAGE_ORDER.map(({ key, label }) => (
              <div key={key}>
                <div className="flex justify-between font-mono text-xs text-white/50">
                  <span>{label}</span>
                  <span>{Math.round(role.probabilities[key] * 100)}%</span>
                </div>
                <ProgressBar percentage={role.probabilities[key] * 100} />
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
