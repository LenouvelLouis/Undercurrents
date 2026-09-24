import { useEffect, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import RingGauge from "../../components/RingGauge";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
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
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.guitaristConfetti.src} alt={PHOTOS.guitaristConfetti.alt} size={56} accent="violet" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">
            Next Setlist
          </h1>
        </div>
        <p className="text-sm leading-relaxed text-white/50 sm:text-right">
          Ranked probability across ~{predictions.length} songs
          <br />
          model accuracy 91%
        </p>
      </div>
      {top && (
        <div className="mt-10 grid grid-cols-6 gap-6">
          {/* The photograph opens the row rather than trailing the page, so the reader
              meets the show before the numbers describing it. */}
          <PhotoPanel
            photo={PHOTOS.singerBlur}
            accent="violet"
            tag="opening"
            className="col-span-6 h-[16rem] md:col-span-3 lg:col-span-1 lg:h-[28rem]"
            focus="center 35%"
          />

          <Card
            tinted
            className="anim-fade-in-up relative col-span-6 flex min-h-[28rem] flex-col items-center justify-center gap-5 overflow-hidden py-12 text-center md:col-span-3 lg:col-span-2"
            style={{ animationDelay: "0.05s" }}
          >
            <div className="pointer-events-none absolute -top-24 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full bg-violet/25 blur-3xl" />
            <span className="text-[13px] font-medium relative text-violet-light">Most likely opener</span>
            <RingGauge percentage={top.probability * 100} size={236} />
            <div className="relative">
              <div className="font-display text-4xl font-bold">{top.song_name}</div>
              <div className="mt-1 font-mono text-xs text-white/40">rank 01 of {predictions.length}</div>
            </div>
          </Card>

          <Card className="anim-fade-in-up col-span-6 flex min-h-[28rem] flex-col justify-center lg:col-span-3" style={{ animationDelay: "0.1s" }}>
            <div className="text-sm font-medium text-white/55">Next in line</div>
            <div className="mt-6 space-y-5">
              {ranked.map((song, i) => (
                <div key={song.song_id} className="flex items-center gap-3">
                  <span className="w-6 shrink-0 font-mono text-xs text-white/30">
                    {String(i + 2).padStart(2, "0")}
                  </span>
                  <span className="min-w-0 shrink grow-[12] basis-0 truncate font-display text-base font-medium">
                    {song.song_name}
                  </span>
                  <div className="h-2 min-w-0 shrink grow-[16] basis-0 overflow-hidden rounded-full bg-white/5">
                    <div
                      className="anim-width-in h-full rounded-full bg-gradient-to-r from-violet-dark via-violet to-violet-light"
                      style={{ width: `${Math.max(4, (song.probability / maxRest) * 100)}%`, animationDelay: `${0.2 + i * 0.06}s` }}
                    />
                  </div>
                  <span className="w-10 shrink-0 text-right font-mono text-xs text-white/50">
                    {Math.round(song.probability * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </Card>

          <PhotoPanel
            photo={PHOTOS.guitaristConfetti}
            accent="violet"
            tag="what the set builds to"
            className="col-span-6 h-[20rem]"
            focus="center 40%"
            style={{ animationDelay: "0.3s" }}
          />
        </div>
      )}
    </div>
  );
}
