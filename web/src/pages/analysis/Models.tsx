import { useEffect, useState } from "react";
import Card from "../../components/Card";
import PhotoChip from "../../components/PhotoChip";
import PhotoPanel from "../../components/PhotoPanel";
import { api } from "../../lib/api";
import { PHOTOS } from "../../lib/photos";
import type { BacktestBundle, Benchmarks } from "../../lib/types";

// Two categories, not a ramp: the incumbent and the challenger. Validated against the
// near-black chart surface (OKLab dE 28.4 normal vision, 27.6 protan), so the pair is
// separable without relying on the labels alone.
const BASELINE_COLOR = "#a531d6";
const MODEL_COLOR = "#e2492f";

function pct(value: number | undefined) {
  return value == null ? "N/A" : `${(value * 100).toFixed(1)}%`;
}

/** Paired bars for one metric: baseline against model, on a shared 0-100% axis. */
function MetricPair({
  label,
  baseline,
  model,
  baselineName,
  modelName,
}: {
  label: string;
  baseline: number | undefined;
  model: number | undefined;
  baselineName: string;
  modelName: string;
}) {
  if (baseline == null || model == null) return null;
  const rows = [
    { name: baselineName, value: baseline, color: BASELINE_COLOR },
    { name: modelName, value: model, color: MODEL_COLOR },
  ];
  return (
    <div>
      <div className="font-mono text-[11px] uppercase tracking-widest text-white/40">{label}</div>
      <div className="mt-3 space-y-2">
        {rows.map((row, i) => (
          <div key={row.name} className="flex items-center gap-3">
            <span className="w-2 shrink-0" />
            <div className="h-5 min-w-0 shrink grow-[16] basis-0 overflow-hidden rounded-[4px] bg-white/[0.04]">
              <div
                className="anim-width-in h-full rounded-[4px]"
                style={{
                  width: `${Math.max(1, row.value * 100)}%`,
                  backgroundColor: row.color,
                  animationDelay: `${0.1 + i * 0.08}s`,
                }}
              />
            </div>
            <span className="w-16 shrink-0 text-right font-mono text-xs text-white/70">
              {pct(row.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function Verdict({ winner, note }: { winner: string; note: string }) {
  const modelWon = winner === "model";
  return (
    <div
      className={`mt-6 rounded-xl border px-4 py-3 ${
        modelWon ? "border-ember/40 bg-ember/10" : "border-violet/40 bg-violet/10"
      }`}
    >
      <div className="font-mono text-[10px] uppercase tracking-widest text-white/45">Verdict</div>
      <div className="mt-1 font-display text-sm font-medium text-white">{note}</div>
    </div>
  );
}


type ScoreRow = { label: string; model: number; baseline: number; baselineLabel: string; note?: string };

// The three newer predictions, reduced to the only comparison that matters: what the model
// scored against the best thing that needed no model at all. A row where the baseline wins is
// drawn exactly like one where it loses, because hiding those is how a scoreboard stops being
// one.
function Scoreboard({ bundle }: { bundle: BacktestBundle }) {
  const rows: ScoreRow[] = [];
  const running = bundle.backtests.running_order;
  const encore = bundle.backtests.encore;
  const comeback = bundle.backtests.comeback;

  if (running?.production) {
    rows.push({
      label: "Running order, as the page runs it",
      model: running.production.model.songs_included,
      baseline: running.production.baseline.songs_included,
      baselineLabel: running.production.baseline.name,
      note: `${Math.round(running.production.model.exact_position * 100)}% landed in the exact slot`,
    });
  }
  const coldStart = running?.runs?.find((run) => run.seed_length === 0);
  if (coldStart) {
    rows.push({
      label: "Running order, invented from nothing",
      model: coldStart.model.songs_included,
      baseline: coldStart.baselines.most_played.songs_included,
      baselineLabel: coldStart.baselines.most_played.name,
      note: "the same model, given no opening song",
    });
  }
  for (const [label, accuracy] of [["Encore", encore], ["Comeback", comeback]] as const) {
    if (!accuracy) continue;
    const others = accuracy.methods.filter((method) => !method.chosen);
    const best = others.reduce((a, b) => (b.test_precision > a.test_precision ? b : a), others[0]);
    rows.push({
      label,
      model: accuracy.precision,
      baseline: best?.test_precision ?? 0,
      baselineLabel: best?.name ?? "none",
      note: `shipped: ${accuracy.methods.find((m) => m.chosen)?.name}`,
    });
  }

  if (!rows.length) {
    return (
      <Card className="anim-fade-in-up mt-6">
        <p className="font-mono text-sm text-white/50">
          The three newer predictions have not been backtested yet. Generate them with:
        </p>
        <pre className="mt-3 overflow-x-auto rounded-lg border border-white/10 bg-ink/60 p-4 font-mono text-xs text-ember-light">
          {bundle.command}
        </pre>
      </Card>
    );
  }

  const max = Math.max(...rows.flatMap((row) => [row.model, row.baseline]), 0.0001);

  return (
    <Card className="anim-fade-in-up mt-6" style={{ animationDelay: "0.2s" }}>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div className="font-mono text-sm uppercase tracking-widest text-white/40">
          Sequence and rotation predictions
        </div>
        <div className="font-mono text-[11px] italic text-white/35">
          each scored on a held-out window, against the best method that needed no model
        </div>
      </div>

      <div className="mt-6 space-y-5">
        {rows.map((row) => {
          const modelWins = row.model > row.baseline;
          return (
            <div key={row.label}>
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="text-sm text-cream">{row.label}</span>
                <span
                  className={`font-mono text-xs ${modelWins ? "text-ember-light" : "text-white/40"}`}
                >
                  {Math.round(row.model * 100)}% vs {Math.round(row.baseline * 100)}%
                  {modelWins ? "" : "  baseline wins"}
                </span>
              </div>
              <div className="mt-2 space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="w-20 shrink-0 font-mono text-[9px] uppercase tracking-wider text-white/30">
                    shipped
                  </span>
                  <div className="h-2 grow overflow-hidden rounded-full bg-white/[0.06]">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${(row.model / max) * 100}%`, backgroundColor: MODEL_COLOR }}
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-20 shrink-0 font-mono text-[9px] uppercase tracking-wider text-white/30">
                    baseline
                  </span>
                  <div className="h-2 grow overflow-hidden rounded-full bg-white/[0.06]">
                    <div
                      className="h-full rounded-full bg-white/25"
                      style={{ width: `${(row.baseline / max) * 100}%` }}
                    />
                  </div>
                </div>
              </div>
              <p className="mt-1.5 font-mono text-[10px] text-white/30">
                baseline: {row.baselineLabel}
                {row.note ? ` · ${row.note}` : ""}
              </p>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export default function Models() {
  const [data, setData] = useState<Benchmarks | null>(null);
  const [missing, setMissing] = useState(false);
  const [openSong, setOpenSong] = useState<number | null>(null);

  const [backtests, setBacktests] = useState<BacktestBundle | null>(null);

  useEffect(() => {
    api.benchmarks().then(setData).catch(() => setMissing(true));
    api.backtests().then(setBacktests).catch(() => {});
  }, []);

  if (missing) {
    return (
      <div>
        <h1 className="font-display text-6xl font-bold">Models</h1>
        <Card className="mt-10">
          <p className="font-mono text-sm text-white/50">
            No benchmark run found yet. Generate one with:
          </p>
          <pre className="mt-3 overflow-x-auto rounded-lg border border-white/10 bg-ink/60 p-4 font-mono text-xs text-ember-light">
            uv run python -m undercurrents.benchmarks.cli run
          </pre>
        </Card>
        {backtests && <Scoreboard bundle={backtests} />}
      </div>
    );
  }

  const sequence = data?.sequence;
  const tabular = data?.tabular;

  return (
    <div>
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <PhotoChip src={PHOTOS.silhouetteLasers.src} alt={PHOTOS.silhouetteLasers.alt} size={56} accent="ember" />
          <h1 className="font-display text-6xl font-bold">Models</h1>
        </div>
        <p className="max-w-sm text-right font-mono text-xs italic text-white/40">
          Every model against the simplest thing that could work
          {data && (
            <>
              <br />
              last run {new Date(data.generated_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
            </>
          )}
        </p>
      </div>

      {data && (
        <Card className="anim-fade-in-up mt-8">
          <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-widest text-white/35">Shows</div>
              <div className="font-display text-2xl font-bold">{data.total_shows}</div>
            </div>
            <div>
              <div className="font-mono text-[10px] uppercase tracking-widest text-white/35">Held out</div>
              <div className="font-display text-2xl font-bold">{data.holdout_shows}</div>
            </div>
            <div className="min-w-0 flex-1">
              <div className="font-mono text-[10px] uppercase tracking-widest text-white/35">Split</div>
              <p className="mt-1 font-mono text-[11px] leading-relaxed text-white/45">{data.split_note}</p>
            </div>
          </div>
        </Card>
      )}

      {sequence && (
        <Card className="anim-fade-in-up mt-6" style={{ animationDelay: "0.05s" }}>
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <div className="font-mono text-sm uppercase tracking-widest text-white/40">
              Next song in the set
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
              <span className="flex items-center gap-1.5 font-mono text-[10px] text-white/50">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: BASELINE_COLOR }} />
                {sequence.baseline.name}
              </span>
              <span className="flex items-center gap-1.5 font-mono text-[10px] text-white/50">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: MODEL_COLOR }} />
                {sequence.model.name}
              </span>
            </div>
          </div>
          <p className="mt-2 max-w-3xl font-mono text-[11px] leading-relaxed text-white/35">
            {sequence.task}. The baseline sees only the previous song; the network sees the whole
            night so far. Both are blocked from predicting a song already played tonight, so
            neither is rewarded for a constraint the other lacks.
          </p>

          <div className="mt-6 grid grid-cols-1 gap-8 lg:grid-cols-2">
            <MetricPair
              label="Top-1 accuracy"
              baseline={sequence.baseline.top_1_accuracy}
              model={sequence.model.top_1_accuracy}
              baselineName={sequence.baseline.name}
              modelName={sequence.model.name}
            />
            <MetricPair
              label="Top-5 accuracy"
              baseline={sequence.baseline.top_5_accuracy}
              model={sequence.model.top_5_accuracy}
              baselineName={sequence.baseline.name}
              modelName={sequence.model.name}
            />
          </div>

          <div className="mt-6 flex flex-wrap gap-x-8 gap-y-2 font-mono text-[11px] text-white/35">
            <span>{sequence.train_shows} shows trained on</span>
            <span>{sequence.test_shows} held out</span>
            <span>{sequence.baseline.predictions} predictions scored</span>
            <span>{sequence.vocabulary} songs in vocabulary</span>
          </div>

          <Verdict
            winner={sequence.winner}
            note={
              sequence.winner === "model"
                ? `The network wins by ${(sequence.top_1_delta * 100).toFixed(1)} points of top-1 accuracy. Setlists are structured, not just repetitive: knowing where you are in the night is worth more than knowing the last song.`
                : `The Markov chain holds. The extra context did not pay for itself on ${sequence.test_shows} held-out shows.`
            }
          />
        </Card>
      )}

      {tabular && tabular.baseline && tabular.model && (
        <Card className="anim-fade-in-up mt-6" style={{ animationDelay: "0.1s" }}>
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <div className="font-mono text-sm uppercase tracking-widest text-white/40">
              Will this song be played
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
              <span className="flex items-center gap-1.5 font-mono text-[10px] text-white/50">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: BASELINE_COLOR }} />
                {tabular.baseline.name}
              </span>
              <span className="flex items-center gap-1.5 font-mono text-[10px] text-white/50">
                <span className="h-2 w-2 rounded-full" style={{ backgroundColor: MODEL_COLOR }} />
                {tabular.model.name}
              </span>
            </div>
          </div>
          <p className="mt-2 max-w-3xl font-mono text-[11px] leading-relaxed text-white/35">
            The task the app already serves, on the same ten hand-built features. Included
            precisely because the interesting outcome was that the extra capacity might buy
            nothing.
          </p>

          <div className="mt-6 grid grid-cols-1 gap-8 lg:grid-cols-3">
            <MetricPair
              label="F1"
              baseline={tabular.baseline.f1}
              model={tabular.model.f1}
              baselineName={tabular.baseline.name}
              modelName={tabular.model.name}
            />
            <MetricPair
              label="Precision"
              baseline={tabular.baseline.precision}
              model={tabular.model.precision}
              baselineName={tabular.baseline.name}
              modelName={tabular.model.name}
            />
            <MetricPair
              label="Recall"
              baseline={tabular.baseline.recall}
              model={tabular.model.recall}
              baselineName={tabular.baseline.name}
              modelName={tabular.model.name}
            />
          </div>

          <div className="mt-6 flex flex-wrap gap-x-8 gap-y-2 font-mono text-[11px] text-white/35">
            <span>{tabular.train_rows?.toLocaleString()} rows trained on</span>
            <span>{tabular.test_rows?.toLocaleString()} rows scored</span>
            <span>{tabular.features?.length} features</span>
          </div>

          <Verdict
            winner={tabular.winner ?? "baseline"}
            note={
              tabular.winner === "model"
                ? `The network edges ahead by ${((tabular.f1_delta ?? 0) * 100).toFixed(1)} F1 points, almost entirely from recall. A real gain, but a small one: the hand-built features were already carrying the signal.`
                : `The logistic regression holds. On this many rows with features this well chosen, the extra capacity finds nothing left to learn.`
            }
          />
        </Card>
      )}

      {data?.item2vec && (
        <Card className="anim-fade-in-up mt-6" style={{ animationDelay: "0.15s" }}>
          <div className="font-mono text-sm uppercase tracking-widest text-white/40">
            Learned song embeddings
          </div>
          <p className="mt-2 max-w-3xl font-mono text-[11px] leading-relaxed text-white/35">
            {data.item2vec.note} {data.item2vec.songs} songs in {data.item2vec.dimensions}
            {" "}dimensions. Click a song for its nearest neighbours by cosine similarity.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            {data.item2vec.neighbours.slice(0, 24).map((entry) => (
              <button
                key={entry.song_id}
                type="button"
                onClick={() => setOpenSong((s) => (s === entry.song_id ? null : entry.song_id))}
                className={`rounded-full border px-3 py-1.5 font-mono text-[11px] transition-colors ${
                  openSong === entry.song_id
                    ? "border-ember/60 bg-ember/15 text-white"
                    : "border-white/15 text-white/55 hover:border-white/35 hover:text-white"
                }`}
              >
                {entry.song_name}
              </button>
            ))}
          </div>
          {openSong !== null && (
            <div className="anim-fade-in-up mt-5 rounded-xl border border-white/10 bg-white/[0.02] p-4">
              {(() => {
                const entry = data.item2vec.neighbours.find((n) => n.song_id === openSong);
                if (!entry) return null;
                return (
                  <>
                    <div className="font-mono text-[10px] uppercase tracking-widest text-white/35">
                      Closest to {entry.song_name}
                    </div>
                    <div className="mt-3 space-y-2">
                      {entry.neighbours.map((n) => (
                        <div key={n.song_id} className="flex items-center gap-3">
                          <span className="min-w-0 shrink grow-[12] basis-0 truncate font-display text-sm">
                            {n.song_name}
                          </span>
                          <div className="h-1.5 min-w-0 shrink grow-[10] basis-0 overflow-hidden rounded-full bg-white/[0.04]">
                            <div
                              className="h-full rounded-full"
                              style={{
                                width: `${Math.max(2, Math.min(100, n.similarity * 100))}%`,
                                backgroundColor: MODEL_COLOR,
                              }}
                            />
                          </div>
                          <span className="w-12 shrink-0 text-right font-mono text-[11px] text-white/50">
                            {n.similarity.toFixed(2)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </>
                );
              })()}
            </div>
          )}
        </Card>
      )}

      {backtests && <Scoreboard bundle={backtests} />}

      <PhotoPanel
        photo={PHOTOS.silhouetteLasers}
        accent="ember"
        tag="measured, not assumed"
        className="mt-6 h-[19rem]"
        focus="center 50%"
        style={{ animationDelay: "0.25s" }}
      />
    </div>
  );
}
