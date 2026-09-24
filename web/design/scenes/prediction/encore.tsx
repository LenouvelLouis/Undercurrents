import { Chart } from "@marver-design/marver/content"
import { Info } from "@phosphor-icons/react"
import { accuracy, candidates, methods } from "./_fixtures.ts"

export const meta = {
  title: "Encore",
  viewport: "laptop",
  theme: "dark",
  description:
    "A prediction page rebuilt to the craft bar: the shipped method, the score it earned on held-out shows, and the simpler rule that beat it, all readable without a legend.",
}

const percent = (value: number) => `${Math.round(value * 100)}%`

function Section({
  title,
  aside,
  children,
}: {
  title: string
  aside?: string
  children: React.ReactNode
}) {
  return (
    <section className="relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02] p-7">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h2 className="font-display text-xl font-semibold tracking-tight text-white text-balance">{title}</h2>
        {aside && <p className="text-sm text-white/40">{aside}</p>}
      </div>
      <div className="mt-6">{children}</div>
    </section>
  )
}

// Validation folds as a scatter against the test score. The spread is the whole point: a mean
// that rests on folds ten points apart cannot separate two methods, and a bar chart of means
// would hide exactly that.
const methodChart = {
  grid: { left: 12, right: 24, top: 12, bottom: 36, containLabel: true },
  xAxis: {
    type: "value",
    min: 0,
    max: 1,
    name: "precision",
    nameLocation: "middle",
    nameGap: 30,
    axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` },
  },
  yAxis: { type: "category", data: [...methods].reverse().map((m) => m.name), axisTick: { show: false } },
  tooltip: { trigger: "item" },
  series: [
    {
      name: "validation folds",
      type: "scatter",
      symbolSize: 7,
      data: [...methods].reverse().flatMap((m, row) => m.folds.map((f) => [f, row])),
      itemStyle: { opacity: 0.55 },
    },
    {
      name: "test window",
      type: "scatter",
      symbol: "diamond",
      symbolSize: 15,
      data: [...methods].reverse().map((m, row) => [m.test, row]),
    },
  ],
}

export default function Encore() {
  const chosen = methods.find((m) => m.chosen)
  const best = methods.reduce((a, b) => (b.test > a.test ? b : a))

  return (
    <div
      className="min-h-screen bg-bg font-body text-white [font-variant-numeric:tabular-nums]"
      // Predictions are violet's half of the product; the charts here inherit that accent.
      style={
        {
          "--mv-accent": "var(--color-violet)",
          "--mv-bg": "var(--color-bg)",
          "--sl-grid": "var(--uc-chart-grid)",
        } as React.CSSProperties
      }
    >
      <div className="mx-auto max-w-[1180px] px-10 py-12">
        <header className="border-b border-white/10 pb-8">
          <h1 className="font-display text-5xl font-bold tracking-tight text-white text-balance">Encore</h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-white/60">
            Which songs close the night. The shipped method calls{" "}
            <span className="text-cream">{percent(accuracy.precision)}</span> of{" "}
            {accuracy.encoreSlots} encore slots correctly across {accuracy.testShows} held-out shows,
            and it is not the best method on that window: {best.name.toLowerCase()} scored{" "}
            <span className="text-cream">{percent(best.test)}</span>.
          </p>
        </header>

        <div className="mt-8 grid grid-cols-[1fr_1.1fr] gap-6">
          <Section title="Most likely to be in it" aside="next show">
            <ol className="space-y-3">
              {candidates.map((candidate) => (
                <li key={candidate.song}>
                  <div className="flex items-baseline justify-between gap-4">
                    <span className="min-w-0 truncate text-[15px] text-white">{candidate.song}</span>
                    <span className="shrink-0 text-sm text-white/50">{percent(candidate.probability)}</span>
                  </div>
                  <div
                    className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-white/[0.07]"
                    role="img"
                    aria-label={`${percent(candidate.probability)} likely`}
                  >
                    <div
                      className="h-full rounded-full bg-violet"
                      style={{ width: `${candidate.probability * 100}%` }}
                    />
                  </div>
                  <p className="mt-1 text-[13px] text-white/35">
                    {candidate.encores} {candidate.encores === 1 ? "encore" : "encores"} across{" "}
                    {candidate.plays} plays
                  </p>
                </li>
              ))}
            </ol>
          </Section>

          <div className="flex flex-col gap-6">
            <Section
              title="Which method ships, and why"
              aside={`${accuracy.validationFolds} validation folds, then one test window`}
            >
              <Chart option={methodChart} h={220} />
              <p className="mt-4 flex gap-2.5 text-sm leading-relaxed text-white/55">
                <Info size={18} weight="fill" className="mt-0.5 shrink-0 text-violet-light/70" />
                <span>
                  Small dots are the three validation folds, diamonds the single test window.{" "}
                  {chosen?.name} was chosen because it led on every fold, and it then lost the test
                  window by{" "}
                  {Math.abs(Math.round(accuracy.marginOverNextBest * 1000) / 10)} points. Re-picking
                  now would turn the test set into a training set, so the result stands as measured.
                </span>
              </p>
            </Section>

            <Section title="What eighteen years of history is worth here" aside="near nothing">
              <p className="text-[15px] leading-relaxed text-white/70">
                Ranking by lifetime encore count scores{" "}
                <span className="text-cream">
                  {percent(methods.find((m) => m.key === "lifetime")?.test ?? 0)}
                </span>
                . The encore is not a hall of fame: it turns over, and what they encored last month
                predicts tonight far better than what they encored across the whole archive.
              </p>
            </Section>
          </div>
        </div>
      </div>
    </div>
  )
}
