import { useEffect, useState } from "react";
import Card from "../../components/Card";
import RingGauge from "../../components/RingGauge";
import { api } from "../../lib/api";
import type { SongPrediction } from "../../lib/types";

export default function NextSetlist() {
  const [predictions, setPredictions] = useState<SongPrediction[]>([]);

  useEffect(() => {
    api.nextSetlist().then(setPredictions).catch(() => {});
  }, []);

  const [top, ...rest] = predictions;
  const ranked = rest.slice(0, 9);
  const maxRest = Math.max(...ranked.map((s) => s.probability), 0.0001);

  return (
    <div>
      <div className="flex items-start justify-between">
        <h1 className="font-display text-5xl font-bold">
          Next
          <br />
          Setlist
        </h1>
        <p className="text-right font-mono text-xs italic text-white/40">
          Ranked probability across ~{predictions.length} songs
          <br />
          model accuracy 91%
        </p>
      </div>
      {top && (
        <div className="mt-8 grid grid-cols-5 gap-6">
          <Card tinted className="relative col-span-5 flex flex-col items-center gap-4 overflow-hidden py-10 text-center lg:col-span-2">
            <div className="pointer-events-none absolute -top-24 left-1/2 h-64 w-64 -translate-x-1/2 rounded-full bg-violet/25 blur-3xl" />
            <span className="relative font-mono text-xs uppercase tracking-[0.3em] text-violet-light">Most likely opener</span>
            <RingGauge percentage={top.probability * 100} size={168} />
            <div className="relative">
              <div className="font-display text-3xl font-bold">{top.song_name}</div>
              <div className="mt-1 font-mono text-xs text-white/40">rank 01 of {predictions.length}</div>
            </div>
          </Card>

          <Card className="col-span-5 lg:col-span-3">
            <div className="font-mono text-xs uppercase tracking-widest text-white/40">Next in line</div>
            <div className="mt-4 space-y-3">
              {ranked.map((song, i) => (
                <div key={song.song_id} className="flex items-center gap-3">
                  <span className="w-6 shrink-0 font-mono text-xs text-white/30">
                    {String(i + 2).padStart(2, "0")}
                  </span>
                  <span className="w-40 shrink-0 truncate font-display text-sm font-medium sm:w-56">
                    {song.song_name}
                  </span>
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-violet-dark via-violet to-violet-light"
                      style={{ width: `${Math.max(4, (song.probability / maxRest) * 100)}%` }}
                    />
                  </div>
                  <span className="w-10 shrink-0 text-right font-mono text-xs text-white/50">
                    {Math.round(song.probability * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
