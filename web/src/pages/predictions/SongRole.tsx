import { useEffect, useState } from "react";
import Card from "../../components/Card";
import ProgressBar from "../../components/ProgressBar";
import { api } from "../../lib/api";
import type { Song, SongRole as SongRoleData } from "../../lib/types";

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
    <div className="mx-auto max-w-xl text-center">
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
          className="w-full rounded-full border border-white/20 bg-white/5 px-5 py-3 text-center text-white outline-none focus:border-magenta"
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
          <h2 className="font-display text-xl font-bold">{role.song_name}</h2>
          <div className="mt-4 space-y-3">
            {(Object.entries(role.probabilities) as [string, number][]).map(([category, probability]) => (
              <div key={category}>
                <div className="flex justify-between font-mono text-xs text-white/50">
                  <span className="capitalize">{category}</span>
                  <span>{Math.round(probability * 100)}%</span>
                </div>
                <ProgressBar percentage={probability * 100} />
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
