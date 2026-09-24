import { useEffect, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import ProgressBar from "../../components/ProgressBar";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { ComebackPrediction } from "../../lib/types";
import { MethodTable } from "./Encore";

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function formatAbsence(days: number, shows: number) {
  const span = days < 400 ? `${days} day${days === 1 ? "" : "s"}` : `${(days / 365.25).toFixed(1)} years`;
  return `${span} · ${shows} show${shows === 1 ? "" : "s"}`;
}

export default function Comeback() {
  const [data, setData] = useState<ComebackPrediction | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api.comebackPrediction().then(setData).catch(() => setFailed(true));
  }, []);

  if (failed) {
    return (
      <div className="font-mono text-sm text-white/50">
        The comeback model has not been trained yet. Run: uv run python -m
        undercurrents.prediction.cli train-models
      </div>
    );
  }
  if (!data) return <div className="font-mono text-sm text-white/40">Loading...</div>;

  const { accuracy } = data;
  const score = (c: { probability: number; recent_play_rate: number; overdue_ratio: number }) =>
    data.method === "model" ? c.probability : data.method === "overdue" ? c.overdue_ratio : c.recent_play_rate;
  const maxScore = Math.max(...data.candidates.map(score), 0.0001);
  const overdueScore = accuracy.methods.find((m) => m.key === "overdue")?.test_precision ?? 0;
  const lift = accuracy.candidate_return_rate
    ? Math.round(accuracy.precision / accuracy.candidate_return_rate)
    : null;

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.artistRedSeats.src} alt={PHOTOS.artistRedSeats.alt} size={56} accent="violet" />
          <h1 className="chroma font-hero text-[clamp(2.4rem,6vw,5.6rem)] font-extrabold uppercase leading-[0.88] tracking-tight">
            Coming Back
          </h1>
        </div>
        <p className="max-w-sm text-sm leading-relaxed text-white/50 sm:text-right">
          Songs missing from the last show, ranked by their odds of returning
          <br />
          {percent(accuracy.precision)} called correctly across {accuracy.return_slots} returns
        </p>
      </div>

      <div className="mt-10 grid grid-cols-1 gap-y-6 xl:grid-cols-[1.15fr_1fr] gap-6">
        <Card className="anim-fade-in-up" tinted accent="violet">
          <p className="text-[13px] font-medium text-white/55">
            Most likely to reappear
          </p>
          <div className="mt-5 space-y-4">
            {data.candidates.map((candidate, i) => (
              <div
                key={candidate.song_id}
                className="anim-fade-in-up"
                style={{ animationDelay: `${i * 0.04}s` }}
              >
                <div className="flex items-baseline justify-between gap-3">
                  <span className="min-w-0 truncate text-sm text-cream">{candidate.song_name}</span>
                  <span className="shrink-0 font-mono text-xs text-white/45">
                    {data.method === "overdue"
                      ? `${candidate.overdue_ratio}x`
                      : percent(score(candidate))}
                  </span>
                </div>
                <div className="mt-1.5">
                  <ProgressBar percentage={(score(candidate) / maxScore) * 100} accent="violet" />
                </div>
                <p className="mt-1 font-mono text-[10px] text-white/30">
                  away {formatAbsence(candidate.days_since_last_play, candidate.shows_since_last_play)} ·{" "}
                  {candidate.play_count} plays all told
                </p>
              </div>
            ))}
          </div>
        </Card>

        <div className="space-y-6">
          <Card className="anim-fade-in-up" style={{ animationDelay: "0.1s" }}>
            <p className="text-[13px] font-medium text-white/55">
              Against picking at random
            </p>
            <div className="mt-4 grid grid-cols-2 gap-4">
              <div>
                <p className="font-display text-4xl font-bold text-cream">{percent(accuracy.precision)}</p>
                <p className="text-[13px] font-medium mt-1 text-white/50">
                  this prediction
                </p>
              </div>
              <div>
                <p className="font-display text-4xl font-bold text-white/40">
                  {percent(accuracy.candidate_return_rate)}
                </p>
                <p className="text-[13px] font-medium mt-1 text-white/50">
                  a candidate at random
                </p>
              </div>
            </div>
            <p className="mt-4 text-[13px] leading-relaxed text-white/40">
              On any given night only {percent(accuracy.candidate_return_rate)} of the shelved songs
              come back{lift ? `, so the ranking is worth about ${lift} times a blind guess` : ""}.
            </p>
          </Card>

          <Card className="anim-fade-in-up" style={{ animationDelay: "0.15s" }}>
            <p className="text-[13px] font-medium text-white/55">
              Which method ships, and why
            </p>
            <p className="mt-2 text-[13px] leading-relaxed text-white/45">
              Picked across {accuracy.validation_folds} separate validation stretches (
              {accuracy.validation_shows} shows), scored once on {accuracy.test_shows} later ones.
              The ticks on each validation bar are the individual folds.
            </p>
            <p className="mt-2 text-[13px] leading-relaxed text-white/45">
              {accuracy.selection.reason.startsWith("kept the simpler")
                ? `The trained model had the higher mean, ${Math.round(accuracy.selection.leader_mean * 1000) / 10}% against ${Math.round(accuracy.selection.chosen_mean * 1000) / 10}%, but a gap that small is smaller than the scatter it sits in. Where the folds cannot tell two methods apart, the simpler one ships.`
                : `The leading method was ahead on the folds by more than they disagreed among themselves, so there was no tie to break.`}
            </p>
            <div className="mt-5">
              <MethodTable methods={accuracy.methods} />
            </div>
          </Card>

          <Card className="anim-fade-in-up" tinted accent="ember" style={{ animationDelay: "0.2s" }}>
            <p className="text-[13px] font-medium text-ember-light/70">
              A word on being "due"
            </p>
            <p className="mt-3 text-[13px] leading-relaxed text-white/50">
              Ranking songs by how overdue they are against their own usual gap scores{" "}
              {percent(overdueScore)}. The intuition that a song is owed a comeback because it has
              been away a long time is, on this data, worth nothing at all. What actually predicts a
              return is the opposite: the song was in most of the last ten shows and simply sat one
              out.
            </p>
          </Card>

          <PhotoPanel
            photo={PHOTOS.synthTable}
            accent="violet"
            tag="Back in the set"
            className="anim-fade-in-up h-44"
            style={{ animationDelay: "0.25s" }}
          />
        </div>
      </div>
    </div>
  );
}
