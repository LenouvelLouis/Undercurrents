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
  const seconds = rest.slice(0, 2);

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
        <div className="mt-8 grid grid-cols-3 gap-4">
          <Card tinted className="col-span-1 flex items-center gap-6">
            <RingGauge percentage={top.probability * 100} size={130} />
            <div>
              <div className="font-mono text-xs uppercase tracking-widest text-magenta-light">Most likely</div>
              <div className="font-display text-2xl font-bold">{top.song_name}</div>
            </div>
          </Card>
          <div className="col-span-1 flex flex-col gap-4">
            {seconds.map((song, i) => (
              <Card key={song.song_id} className="flex items-center gap-4">
                <RingGauge percentage={song.probability * 100} size={70} />
                <div>
                  <div className="font-mono text-xs text-white/40">#{String(i + 2).padStart(2, "0")}</div>
                  <div className="font-display font-bold">{song.song_name}</div>
                </div>
              </Card>
            ))}
          </div>
          <Card className="col-span-1 flex items-center justify-center border-dashed text-white/30">
            <p className="font-mono text-xs">full ranked list — {predictions.length} songs</p>
          </Card>
        </div>
      )}
    </div>
  );
}
