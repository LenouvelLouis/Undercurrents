import { useEffect, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { Overview, SetlistLength } from "../../lib/types";

const TICKS = [0, 5, 10, 15, 20, 25, 30, 35, 40];

export default function ConcertLength() {
  const [length, setLength] = useState<SetlistLength | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);

  useEffect(() => {
    api.setlistLength().then(setLength).catch(() => {});
    api.overview().then(setOverview).catch(() => {});
  }, []);

  const predicted = length?.predicted_songs ?? null;
  // The model's real, already-computed mean absolute error (same figure quoted in the
  // footer stat bar) doubles as an honest "typical range" around the point estimate,
  // rather than inventing a spread the API never reported.
  const mae = overview?.length_mae_songs ?? null;
  const scaleMax = Math.max(...TICKS, predicted !== null ? Math.ceil((predicted + (mae ?? 0)) * 1.3) : 0);
  const markerPct = predicted !== null ? Math.min(100, (predicted / scaleMax) * 100) : 0;
  const lowPct = predicted !== null && mae !== null ? Math.max(0, ((predicted - mae) / scaleMax) * 100) : markerPct;
  const highPct = predicted !== null && mae !== null ? Math.min(100, ((predicted + mae) / scaleMax) * 100) : markerPct;

  return (
    <div>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.singerConfetti.src} alt={PHOTOS.singerConfetti.alt} size={56} accent="violet" />
          <h1 className="font-display text-6xl font-bold">
            Concert
            <br />
            Length
          </h1>
        </div>
        <p className="text-right font-mono text-xs italic text-white/40">
          Predicted song count for the next show
        </p>
      </div>

      {/* Six columns rather than five, so a photograph can take a slot of its own between
          the prediction blocks instead of being appended after all of them. */}
      <div className="mt-10 grid grid-cols-6 gap-6">
        <Card tinted className="anim-fade-in-up relative col-span-6 flex min-h-[26rem] flex-col items-center justify-center overflow-hidden py-16 text-center md:col-span-3 lg:col-span-2">
          <div className="pointer-events-none absolute -bottom-24 left-1/2 h-72 w-72 -translate-x-1/2 rounded-full bg-violet/25 blur-3xl" />
          <span className="relative font-display text-[9rem] font-bold leading-none">{predicted ?? "N/A"}</span>
          <span className="relative mt-3 font-mono text-sm uppercase tracking-widest text-white/50">songs (mean)</span>
          {mae !== null && (
            <span className="relative mt-2 font-mono text-xs text-white/35">± {mae} songs, mean absolute error</span>
          )}
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
          <div className="font-mono text-sm uppercase tracking-widest text-white/40">Where it lands on the scale</div>
          <div className="relative mt-14 h-3 rounded-full bg-white/5">
            {mae !== null && (
              <div
                className="absolute top-1/2 -translate-y-1/2 rounded-full bg-violet/25"
                style={{ left: `${lowPct}%`, width: `${Math.max(0, highPct - lowPct)}%`, height: "16px" }}
              />
            )}
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
          {mae !== null && (
            <div className="mt-6 font-mono text-xs text-white/30">
              shaded band: typical range of {Math.max(0, (predicted ?? 0) - mae)}–{(predicted ?? 0) + mae} songs
            </div>
          )}
        </Card>

        {/* Stat row, split down the middle by a second photograph. */}
        <Card className="anim-fade-in-up col-span-3 flex flex-col justify-center lg:col-span-1" style={{ animationDelay: "0.15s" }}>
          <div className="font-mono text-xs uppercase tracking-widest text-white/40">Predicted mean</div>
          <div className="mt-2 font-display text-4xl font-bold">{predicted ?? "N/A"}</div>
          <div className="font-mono text-[10px] text-white/30">songs, next show</div>
        </Card>
        <Card className="anim-fade-in-up col-span-3 flex flex-col justify-center lg:col-span-1" style={{ animationDelay: "0.2s" }}>
          <div className="font-mono text-xs uppercase tracking-widest text-white/40">Mean absolute error</div>
          <div className="mt-2 font-display text-4xl font-bold">{mae ?? "N/A"}</div>
          <div className="font-mono text-[10px] text-white/30">songs, model-wide</div>
        </Card>

        <PhotoPanel
          photo={PHOTOS.singerConfetti}
          accent="violet"
          className="col-span-6 h-[14rem] lg:col-span-2 lg:h-[15rem]"
          style={{ animationDelay: "0.22s" }}
        />

        <Card className="anim-fade-in-up col-span-3 flex flex-col justify-center lg:col-span-1" style={{ animationDelay: "0.25s" }}>
          <div className="font-mono text-xs uppercase tracking-widest text-white/40">Typical range</div>
          <div className="mt-2 font-display text-4xl font-bold">
            {predicted !== null && mae !== null ? `${Math.max(0, predicted - mae)}–${predicted + mae}` : "N/A"}
          </div>
          <div className="font-mono text-[10px] text-white/30">songs, within one MAE</div>
        </Card>
        <Card className="anim-fade-in-up col-span-3 flex flex-col justify-center lg:col-span-1" style={{ animationDelay: "0.3s" }}>
          <div className="font-mono text-xs uppercase tracking-widest text-white/40">Setlist accuracy</div>
          <div className="mt-2 font-display text-4xl font-bold">
            {overview?.setlist_accuracy != null ? `${Math.round(overview.setlist_accuracy * 100)}%` : "N/A"}
          </div>
          <div className="font-mono text-[10px] text-white/30">over {overview?.concerts_logged ?? "?"} concerts</div>
        </Card>

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
