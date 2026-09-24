import { useEffect, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { SetlistDuration, SetlistLength } from "../../lib/types";

const TICKS = [0, 5, 10, 15, 20, 25, 30, 35, 40];

export default function ConcertLength() {
  const [length, setLength] = useState<SetlistLength | null>(null);
  const [duration, setDuration] = useState<SetlistDuration | null>(null);

  useEffect(() => {
    api.setlistLength().then(setLength).catch(() => {});
    api.setlistDuration().then(setDuration).catch(() => {});
  }, []);

  const predicted = length?.predicted_songs ?? null;
  const scaleMax = Math.max(...TICKS, predicted !== null ? Math.ceil(predicted * 1.3) : 0);
  const markerPct = predicted !== null ? Math.min(100, (predicted / scaleMax) * 100) : 0;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.singerConfetti.src} alt={PHOTOS.singerConfetti.alt} size={56} accent="violet" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">
            Concert Length
          </h1>
        </div>
        <p className="text-sm leading-relaxed text-white/50 sm:text-right">
          Predicted song count for the next show
        </p>
      </div>

      {/* Six columns rather than five, so a photograph can take a slot of its own between
          the prediction blocks instead of being appended after all of them. */}
      <div className="mt-10 grid grid-cols-6 gap-6">
        <Card tinted className="anim-fade-in-up relative col-span-6 flex min-h-[26rem] flex-col items-center justify-center overflow-hidden py-16 text-center md:col-span-3 lg:col-span-2">
          <div className="pointer-events-none absolute -bottom-24 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full bg-violet/25 blur-3xl" />
          <span className="relative font-display text-[9rem] font-bold leading-none">{predicted ?? "N/A"}</span>
          <span className="text-sm font-medium relative mt-3 text-white/50">songs (mean)</span>
        </Card>

        <PhotoPanel
          photo={PHOTOS.stageRainbowLights}
          accent="violet"
          tag="on stage"
          className="col-span-6 min-h-[16rem] md:col-span-3 lg:col-span-1 lg:min-h-[26rem]"
          focus="center 40%"
          style={{ animationDelay: "0.05s" }}
        />

        <Card className="anim-fade-in-up col-span-6 flex min-h-[26rem] flex-col justify-center lg:col-span-3" style={{ animationDelay: "0.1s" }}>
          <div className="text-sm font-medium text-white/55">Where it lands on the scale</div>
          <div className="relative mt-14 h-3 rounded-full bg-white/5">
            <div
              className="anim-width-in h-full rounded-full bg-gradient-to-r from-violet-dark via-violet to-violet-light"
              style={{ width: `${markerPct}%`, animationDelay: "0.3s" }}
            />
            {predicted !== null && (
              <div
                className="absolute -top-4 flex -translate-x-1/2 flex-col items-center"
                style={{ left: `${markerPct}%` }}
              >
                <span className="rounded-full bg-violet px-2.5 py-1 font-mono text-xs font-bold text-ink shadow-glow-violet">
                  {predicted}
                </span>
                <span className="mt-1 h-4 w-px bg-violet-light" />
              </div>
            )}
          </div>
          <div className="mt-8 flex justify-between font-mono text-xs text-white/30">
            {TICKS.map((tick) => (
              <span key={tick} className="flex flex-col items-center gap-1">
                <span className="h-2 w-px bg-white/15" />
                {tick}
              </span>
            ))}
          </div>
        </Card>

        {/* Stat row: the point estimate beside a second photograph. */}
        <Card className="anim-fade-in-up col-span-6 flex flex-col justify-center md:col-span-2" style={{ animationDelay: "0.15s" }}>
          <div className="text-[13px] font-medium text-white/55">Predicted mean</div>
          <div className="mt-2 font-display text-4xl font-bold">{predicted ?? "N/A"}</div>
          <div className="font-mono text-[10px] text-white/30">songs, next show</div>
        </Card>

        <PhotoPanel
          photo={PHOTOS.singerConfetti}
          accent="violet"
          className="col-span-6 h-[14rem] md:col-span-4 lg:h-[15rem]"
          style={{ animationDelay: "0.22s" }}
        />


        {/* Runtime in minutes. Shown next to the measured history rather than alone, because
            the minutes figure is a product of two real numbers, not a trained prediction. */}
        {duration && (
          <>
            <Card tinted className="anim-fade-in-up relative col-span-6 flex flex-col items-center justify-center overflow-hidden py-12 text-center md:col-span-3 lg:col-span-2" style={{ animationDelay: "0.32s" }}>
              <div className="pointer-events-none absolute -top-24 left-1/2 h-64 w-64 -translate-x-1/2 rounded-full bg-violet/20 blur-3xl" />
              <span className="text-[13px] font-medium relative text-violet-light">Estimated runtime</span>
              <span className="relative mt-4 font-display text-7xl font-bold leading-none">
                {Math.round(duration.predicted_minutes)}
                <span className="ml-2 font-mono text-2xl font-normal text-white/50">min</span>
              </span>
              <span className="relative mt-3 max-w-[16rem] text-[13px] leading-relaxed text-white/40">
                {duration.predicted_songs} songs at {duration.mean_song_minutes} min average
              </span>
            </Card>

            <Card className="anim-fade-in-up col-span-6 md:col-span-3 lg:col-span-4" style={{ animationDelay: "0.36s" }}>
              <div className="text-sm font-medium text-white/55">
                What the archive actually measured
              </div>
              <div className="mt-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
                <div>
                  <div className="text-[13px] font-medium text-white/50">Mean runtime</div>
                  <div className="mt-1 font-display text-3xl font-bold">
                    {duration.measured_mean_minutes ?? "N/A"}
                    <span className="ml-1 font-mono text-sm font-normal text-white/40">min</span>
                  </div>
                </div>
                <div>
                  <div className="text-[13px] font-medium text-white/50">Median runtime</div>
                  <div className="mt-1 font-display text-3xl font-bold">
                    {duration.measured_median_minutes ?? "N/A"}
                    <span className="ml-1 font-mono text-sm font-normal text-white/40">min</span>
                  </div>
                </div>
                <div>
                  <div className="text-[13px] font-medium text-white/50">Shows timed</div>
                  <div className="mt-1 font-display text-3xl font-bold">{duration.measured_shows}</div>
                  <div className="font-mono text-[10px] text-white/30">of {duration.shows_total} logged</div>
                </div>
                <div>
                  <div className="text-[13px] font-medium text-white/50">Duration known</div>
                  <div className="mt-1 font-display text-3xl font-bold">
                    {duration.duration_coverage != null ? `${Math.round(duration.duration_coverage * 100)}%` : "N/A"}
                  </div>
                  <div className="font-mono text-[10px] text-white/30">of performances</div>
                </div>
              </div>
              <p className="mt-6 text-[13px] leading-relaxed text-white/30">
                The runtime is an estimate, not a separate model: {duration.method}. Only shows
                where every performed song has a known duration are counted in the measured
                figures, which is why {duration.measured_shows} of {duration.shows_total} qualify.
              </p>
            </Card>
          </>
        )}

        {/* Closing band: one wide photograph the width of the whole page. */}
        <PhotoPanel
          photo={PHOTOS.silhouetteLasers}
          accent="violet"
          tag="the room it has to fill"
          className="col-span-6 h-[20rem]"
          focus="center 45%"
          style={{ animationDelay: "0.35s" }}
        />
      </div>
    </div>
  );
}
