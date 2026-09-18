import { useEffect, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import ProgressBar from "../../components/ProgressBar";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { MethodScore } from "../../lib/types";
import type { EncorePrediction } from "../../lib/types";

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

// Every method that was in the running, with the window that chose the winner kept visually
// separate from the window that scored it. Collapsing the two into one number is exactly the
// mistake this layout exists to prevent.
export function MethodTable({ methods }: { methods: MethodScore[] }) {
  const max = Math.max(...methods.map((m) => Math.max(m.validation_precision, m.test_precision)), 0.0001);
  return (
    <div className="space-y-4">
      {methods.map((method) => (
        <div key={method.key}>
          <div className="flex items-baseline justify-between gap-3">
            <span
              className={`min-w-0 truncate text-sm ${method.chosen ? "text-cream" : "text-white/45"}`}
            >
              {method.name}
              {method.chosen && (
                <span className="ml-2 font-mono text-[9px] uppercase tracking-wider text-violet-light">
                  chosen
                </span>
              )}
            </span>
            <span className="shrink-0 font-mono text-xs text-white/50">
              {percent(method.test_precision)}
            </span>
          </div>
          <div className="mt-1.5 space-y-1">
            <div className="flex items-center gap-2">
              <span className="w-20 shrink-0 font-mono text-[9px] uppercase tracking-wider text-white/30">
                validation
              </span>
              <div className="relative h-1.5 grow rounded-full bg-white/[0.06]">
                <div
                  className="h-full rounded-full bg-white/25"
                  style={{ width: `${(method.validation_precision / max) * 100}%` }}
                />
                {/* one tick per fold, so a mean resting on a wide spread cannot pass for a
                    settled result */}
                {method.fold_precisions.map((fold, i) => (
                  <span
                    key={i}
                    className="absolute top-1/2 h-2.5 w-px -translate-y-1/2 bg-white/50"
                    style={{ left: `${Math.min(100, (fold / max) * 100)}%` }}
                  />
                ))}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-20 shrink-0 font-mono text-[9px] uppercase tracking-wider text-white/30">
                test
              </span>
              <div className="h-1.5 grow rounded-full bg-white/[0.06]">
                <div
                  className={`h-full rounded-full ${
                    method.chosen
                      ? "bg-gradient-to-r from-violet-dark via-violet to-violet-light"
                      : "bg-white/25"
                  }`}
                  style={{ width: `${(method.test_precision / max) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function Encore() {
  const [data, setData] = useState<EncorePrediction | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.encorePrediction().then(setData).catch(() => setFailed(true));
  }, []);

  if (failed) {
    return (
      <div className="font-mono text-sm text-white/50">
        The encore model has not been trained yet. Run: uv run python -m
        undercurrents.prediction.cli train-models
      </div>
    );
  }
  if (!data) return <div className="font-mono text-sm text-white/40">Loading...</div>;

  const { accuracy } = data;
  const maxScore = Math.max(
    ...data.candidates.map((c) => (data.method === "model" ? c.probability : c.recent_encore_rate)),
    0.0001,
  );
  const lostBy = accuracy.margin_over_next_best < 0;

  return (
    <div>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.singerConfetti.src} alt={PHOTOS.singerConfetti.alt} size={56} accent="violet" />
          <h1 className="font-display text-6xl font-bold">Encore</h1>
        </div>
        <p className="max-w-sm text-right font-mono text-xs italic text-white/40">
          What closes the night
          <br />
          {percent(accuracy.precision)} of {accuracy.encore_slots} encore slots called correctly
        </p>
      </div>

      <div className="mt-10 grid grid-cols-[1.15fr_1fr] gap-6">
        <Card className="anim-fade-in-up" tinted accent="violet">
          <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/40">
            Most likely to be in it
          </p>
          <div className="mt-5 space-y-4">
            {data.candidates.map((candidate, i) => {
              const score = data.method === "model" ? candidate.probability : candidate.recent_encore_rate;
              return (
                <div
                  key={candidate.song_id}
                  className="anim-fade-in-up"
                  style={{ animationDelay: `${i * 0.04}s` }}
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="min-w-0 truncate text-sm text-cream">{candidate.song_name}</span>
                    <span className="shrink-0 font-mono text-xs text-white/45">
                      {percent(score)}
                    </span>
                  </div>
                  <div className="mt-1.5">
                    <ProgressBar percentage={(score / maxScore) * 100} accent="violet" />
                  </div>
                  <p className="mt-1 font-mono text-[10px] text-white/30">
                    {candidate.encore_count} encore{candidate.encore_count === 1 ? "" : "s"} across{" "}
                    {candidate.play_count} plays
                  </p>
                </div>
              );
            })}
          </div>
        </Card>

        <div className="space-y-6">
          <Card className="anim-fade-in-up" style={{ animationDelay: "0.1s" }}>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/40">
              Which method ships, and why
            </p>
            <p className="mt-2 font-mono text-[11px] leading-relaxed text-white/45">
              {accuracy.methods.length} candidate methods, each asked to name as many songs as that
              night's encore actually held. The winner was picked across{" "}
              {accuracy.validation_folds} separate validation stretches ({accuracy.validation_shows}{" "}
              shows in all), then scored once on {accuracy.test_shows} later ones it had never seen.
              The ticks on each validation bar are the individual folds.
            </p>
            <div className="mt-5">
              <MethodTable methods={accuracy.methods} />
            </div>
            <p className="mt-4 font-mono text-[11px] leading-relaxed text-white/45">
              {accuracy.selection.reason.startsWith("kept the simpler")
                ? `The highest mean belonged to ${accuracy.selection.leader} at ${Math.round(accuracy.selection.leader_mean * 1000) / 10}%, but its lead was inside the fold-to-fold scatter, so the simpler method was kept instead.`
                : `No tie to break: the leading method was ahead on the folds by more than they disagreed among themselves.`}
            </p>
            <p className="mt-5 border-t border-white/10 pt-4 font-mono text-[11px] leading-relaxed text-white/40">
              {lostBy ? (
                <>
                  Worth saying plainly: on the test window another method beat the chosen one by{" "}
                  {Math.abs(Math.round(accuracy.margin_over_next_best * 1000) / 10)} points. It was not
                  picked, because picking it would have meant reading the answer off the test set,
                  which is how a model ends up looking better on a page than it is on a night.
                </>
              ) : (
                <>
                  The chosen method held its lead on the test window, by{" "}
                  {Math.round(accuracy.margin_over_next_best * 1000) / 10} points over the next best.
                </>
              )}
            </p>
          </Card>

          <Card className="anim-fade-in-up" style={{ animationDelay: "0.15s" }}>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-white/40">
              What history is worth here
            </p>
            <p className="mt-3 font-mono text-[11px] leading-relaxed text-white/45">
              Ranking by lifetime encore count scores{" "}
              {percent(accuracy.methods.find((m) => m.key === "lifetime")?.test_precision ?? 0)}, near
              nothing. The encore is not a hall of fame: it turns over, and what they encored last
              month predicts tonight far better than what they encored across eighteen years.
            </p>
          </Card>

          <PhotoPanel
            photo={PHOTOS.stageRainbowLights}
            accent="violet"
            tag="THE LAST SONGS"
            className="anim-fade-in-up h-44"
            style={{ animationDelay: "0.2s" }}
          />
        </div>
      </div>
    </div>
  );
}
