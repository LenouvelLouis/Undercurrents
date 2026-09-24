import { useEffect, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { RunningOrder as RunningOrderData, RunningOrderRun } from "../../lib/types";

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

// The accuracy sweep, drawn as one row per seed length. The point it has to make visually is
// that the model is weak with no seed and strong with one, so the baseline sits on the same
// row rather than in a separate table where the comparison would be lost.
function SeedSweep({ runs }: { runs: RunningOrderRun[] }) {
  const max = Math.max(
    ...runs.flatMap((run) => [run.model.songs_included, run.baselines.most_played.songs_included]),
    0.0001,
  );

  return (
    <div className="space-y-5">
      {runs.map((run) => {
        const modelWidth = (run.model.songs_included / max) * 100;
        const baseWidth = (run.baselines.most_played.songs_included / max) * 100;
        return (
          <div key={run.seed_length}>
            <div className="flex items-baseline justify-between font-mono text-xs text-white/50">
              <span>
                {run.seed_length === 0 ? "no songs given" : `first ${run.seed_length} song${run.seed_length > 1 ? "s" : ""} given`}
              </span>
              <span className={run.winner === "model" ? "text-violet-light" : "text-white/40"}>
                {percent(run.model.songs_included)} vs {percent(run.baselines.most_played.songs_included)}
              </span>
            </div>
            <div className="mt-2 space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-medium w-16 shrink-0 text-violet-light/70">model</span>
                <div className="h-2.5 grow rounded-full bg-white/[0.06]">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-violet-dark via-violet to-violet-light"
                    style={{ width: `${modelWidth}%` }}
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[13px] font-medium w-16 shrink-0 text-white/50">most played</span>
                <div className="h-2.5 grow rounded-full bg-white/[0.06]">
                  <div className="h-full rounded-full bg-white/25" style={{ width: `${baseWidth}%` }} />
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function RunningOrder() {
  const [data, setData] = useState<RunningOrderData | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.runningOrder().then(setData).catch(() => setFailed(true));
  }, []);

  if (failed) {
    return (
      <div className="font-mono text-sm text-white/50">
        The running-order model has not been trained yet. Run: uv run python -m
        undercurrents.prediction.cli train-models
      </div>
    );
  }
  if (!data) return <div className="font-mono text-sm text-white/40">Loading...</div>;

  const production = data.accuracy.production;
  const coldRun = data.accuracy.runs.find((run) => run.seed_length === 0);
  const oneSeedRun = data.accuracy.runs.find((run) => run.seed_length === 1);
  const maxConfidence = Math.max(...data.order.map((entry) => entry.confidence), 0.0001);

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.roundStageAerial.src} alt={PHOTOS.roundStageAerial.alt} size={56} accent="violet" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">
            Running Order
          </h1>
        </div>
        <p className="max-w-sm text-sm leading-relaxed text-white/50 sm:text-right">
          The set written out first song to last, not just which songs
          <br />
          {percent(production.model.songs_included)} of the set right, trained on{" "}
          {data.trained_on_shows} shows
        </p>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-y-6 xl:grid-cols-[1.15fr_1fr] gap-6">
        <Card className="anim-fade-in-up" tinted accent="violet">
          <p className="text-[13px] font-medium text-white/55">
            Predicted set · {data.length} songs
          </p>
          <p className="mt-1 text-[13px] italic text-white/35">
            length {data.length_source}
          </p>

          <div className="mt-5 space-y-2">
            {data.seed.map((entry) => (
              <div key={`seed-${entry.position}`} className="flex items-center gap-3">
                <span className="w-6 shrink-0 text-right font-mono text-xs text-white/30">{entry.position}</span>
                <span className="min-w-0 shrink grow-[12] basis-0 truncate text-sm text-white/45">{entry.song_name}</span>
                <span className="text-[13px] font-medium shrink-0 text-white/40">given</span>
              </div>
            ))}
            {data.order.map((entry, i) => (
              <div
                key={`pred-${entry.position}`}
                className="anim-fade-in-up flex items-center gap-3"
                style={{ animationDelay: `${i * 0.03}s` }}
              >
                <span className="w-6 shrink-0 text-right font-mono text-xs text-white/40">{entry.position}</span>
                <span className="min-w-0 shrink grow-[12] basis-0 truncate text-sm text-cream">{entry.song_name}</span>
                <div className="h-1.5 shrink grow-[8] basis-0 rounded-full bg-white/[0.06]">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-violet-dark via-violet to-violet-light"
                    style={{ width: `${(entry.confidence / maxConfidence) * 100}%` }}
                  />
                </div>
                <span className="w-10 shrink-0 text-right font-mono text-[10px] text-white/35">
                  {percent(entry.confidence)}
                </span>
              </div>
            ))}
          </div>

          <p className="mt-6 border-t border-white/10 pt-4 text-[13px] leading-relaxed text-white/40">
            The first {data.seed_length} {data.seed_length === 1 ? "song is" : "songs are"} not a
            prediction: {data.seed_source}. Everything below it is the model continuing from there,
            feeding each of its own guesses back in. Confidence is the chosen song's share of the
            probability left among the songs not yet played that night.
          </p>
        </Card>

        <div className="space-y-6">
          <Card className="anim-fade-in-up" style={{ animationDelay: "0.1s" }}>
            <p className="text-[13px] font-medium text-white/55">
              How much the opening songs are worth
            </p>
            <p className="mt-2 text-[13px] leading-relaxed text-white/45">
              Share of the remaining set the model gets right, on {data.accuracy.test_shows} held-out
              shows, against the flattest baseline there is: the most played songs, the same list
              every night.
            </p>
            <div className="mt-5">
              <SeedSweep runs={data.accuracy.runs} />
            </div>
            <p className="mt-5 border-t border-white/10 pt-4 text-[13px] leading-relaxed text-white/40">
              {data.accuracy.model_beats_baselines_from_seed === null ? (
                <>
                  The model does not beat the static list at any seed length tested. It is shown here
                  because the order it proposes is a real sequence rather than a leaderboard, but on
                  raw song inclusion the leaderboard wins, and that is worth knowing before trusting
                  the set above.
                </>
              ) : (
                <>
                  One real song changes everything. With nothing to go on the model recovers{" "}
                  {coldRun ? percent(coldRun.model.songs_included) : "n/a"} of the set, worse than the
                  static list. Told only what they actually opened with, it recovers{" "}
                  {oneSeedRun ? percent(oneSeedRun.model.songs_included) : "n/a"}. The set is far more
                  predictable from inside it than from outside it, which is the whole reason this page
                  is framed around continuing a night rather than inventing one.
                </>
              )}
            </p>
          </Card>

          <Card className="anim-fade-in-up" style={{ animationDelay: "0.15s" }}>
            <p className="text-[13px] font-medium text-white/55">
              This prediction, measured as it runs
            </p>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div>
                <p className="font-display text-4xl font-bold text-cream">
                  {percent(production.model.songs_included)}
                </p>
                <p className="text-[13px] font-medium mt-1 text-white/50">
                  songs in the set
                </p>
              </div>
              <div>
                <p className="font-display text-4xl font-bold text-cream">
                  {percent(production.model.exact_position)}
                </p>
                <p className="text-[13px] font-medium mt-1 text-white/50">
                  at the exact slot
                </p>
              </div>
            </div>
            <p className="mt-4 text-[13px] leading-relaxed text-white/40">
              Scored the way the page actually works, over {production.shows_scored} held-out shows:
              seeded with the previous night's opening rather than tonight's, and with those seeded
              songs counted as guesses like any other. Against{" "}
              {percent(production.baseline.songs_included)} for the static most-played list.
            </p>
            <p className="mt-3 text-[13px] leading-relaxed text-white/40">
              The whole thing rests on one assumption, so here it is: consecutive shows open with the
              same song {percent(production.opener_repeat_rate)} of the time. When they do, the set
              below is close to right. When they do not, the model is continuing a night that never
              happened.
            </p>
          </Card>

          <PhotoPanel
            photo={PHOTOS.silhouetteLasers}
            accent="violet"
            tag="ONE NIGHT, IN ORDER"
            className="anim-fade-in-up h-48"
            style={{ animationDelay: "0.2s" }}
          />
        </div>
      </div>
    </div>
  );
}
