import { Chart } from "@marver-design/marver/content"
import { ArrowUpRight, CheckCircle, MicrophoneStage, Warning } from "@phosphor-icons/react"
import { debutCheck, flags, formats, guests, notesTotal, teases } from "./_fixtures.ts"

export const meta = {
  title: "Night Notes",
  viewport: "laptop",
  // The product has one theme. Pinning it here keeps the frame in the world it was
  // designed for rather than following a canvas-wide theme toggle it has no answer to.
  theme: "dark",
  description:
    "A dense analysis page rebuilt to the craft bar: one real chart instead of hand-drawn bars, drawn icons, and figures set in sentences rather than as oversized stat heroes.",
}

// One shared surface. There is exactly one card level on this page: a section sits
// directly on the ground with a hairline, and nothing nests inside another card.
function Section({
  title,
  aside,
  children,
  className = "",
}: {
  title: string
  aside?: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <section
      className={`relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02] p-7 ${className}`}
    >
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
      <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
        <h2 className="font-display text-xl font-semibold tracking-tight text-white text-balance">
          {title}
        </h2>
        {aside && <p className="text-sm text-white/40">{aside}</p>}
      </div>
      <div className="mt-6">{children}</div>
    </section>
  )
}

const formatChart = {
  grid: { left: 130, right: 32, top: 8, bottom: 24 },
  xAxis: { type: "value", name: "shows", nameLocation: "middle", nameGap: 28 },
  yAxis: {
    type: "category",
    data: [...formats].reverse().map((f) => f.name),
    axisTick: { show: false },
  },
  tooltip: {
    trigger: "axis",
    axisPointer: { type: "shadow" },
    formatter: (params: { name: string; value: number }[]) => {
      const row = formats.find((f) => f.name === params[0].name)
      return `${params[0].name}<br/>${row?.shows} shows, ${row?.songs} songs`
    },
  },
  series: [
    {
      type: "bar",
      data: [...formats].reverse().map((f) => f.shows),
      barMaxWidth: 18,
      itemStyle: { borderRadius: [0, 3, 3, 0] },
    },
  ],
}

const flagChart = {
  grid: { left: 210, right: 40, top: 8, bottom: 24 },
  xAxis: { type: "value", name: "notes", nameLocation: "middle", nameGap: 28 },
  yAxis: {
    type: "category",
    data: [...flags].reverse().map((f) => f.label),
    axisTick: { show: false },
    axisLabel: { width: 200, overflow: "truncate" },
  },
  tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
  series: [
    {
      type: "bar",
      data: [...flags].reverse().map((f) => f.count),
      barMaxWidth: 14,
      itemStyle: { borderRadius: [0, 3, 3, 0] },
    },
  ],
}

export default function NightNotes() {
  return (
    <div
      className="min-h-screen bg-bg font-body text-white [font-variant-numeric:tabular-nums]"
      // marver's Chart reads its accent, ground and gridline from these custom properties and
      // otherwise falls back to a blue that belongs to no brand. Analysis is ember's half of
      // the product, so that is the accent the charts on this page inherit.
      style={
        {
          "--mv-accent": "var(--color-ember)",
          "--mv-bg": "var(--color-bg)",
          "--sl-grid": "var(--uc-chart-grid)",
        } as React.CSSProperties
      }
    >
      <div className="mx-auto max-w-[1180px] px-10 py-12">
        <header className="flex flex-wrap items-end justify-between gap-6 border-b border-white/10 pb-8">
          <div>
            <h1 className="font-display text-5xl font-bold tracking-tight text-white text-balance">
              Night Notes
            </h1>
            <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-white/60">
              What happened on the night, as opposed to which songs were played. Drawn from{" "}
              <span className="text-cream">{notesTotal} margin notes</span> and{" "}
              <span className="text-cream">{guests.length} credited guest appearances</span>, all of
              which shipped inside the setlist payloads and went unread for eighteen years.
            </p>
          </div>
          <a
            href="#"
            className="group inline-flex cursor-pointer items-center gap-2 rounded-full border border-ember/40 px-4 py-2 text-sm text-ember-light outline-none transition-colors hover:border-ember hover:bg-ember/10 focus-visible:ring-2 focus-visible:ring-ember-light focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          >
            Open the source notes
            <ArrowUpRight size={16} weight="bold" className="transition-transform group-hover:translate-x-0.5" />
          </a>
        </header>

        <div className="mt-8 grid grid-cols-[1.15fr_1fr] gap-6">
          <Section
            title="How the show was shaped"
            aside="named segments, by the shows that had one"
          >
            <Chart option={formatChart} h={300} />
            <p className="mt-5 text-sm leading-relaxed text-white/50">
              A B-Stage is a satellite platform out in the crowd, and it is far more common than it
              looks from a setlist: 56 nights carry one, averaging 2.4 songs. Twice the segment name
              is an album title, which marks a record played end to end.
            </p>
          </Section>

          <Section title="Who else was on stage" aside="complete, not inferred">
            <ul className="divide-y divide-white/[0.07]">
              {guests.map((guest) => (
                <li
                  key={`${guest.guest}-${guest.date}-${guest.song}`}
                  className="flex items-center gap-4 py-2.5"
                >
                  <MicrophoneStage size={18} weight="regular" className="shrink-0 text-ember/70" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[15px] text-white">{guest.guest}</p>
                    <p className="truncate text-[13px] text-white/40">
                      {guest.song} · {guest.city}
                    </p>
                  </div>
                  <time className="shrink-0 text-[13px] text-white/35" dateTime={guest.date}>
                    {new Date(`${guest.date}T00:00:00`).toLocaleDateString("en-GB", {
                      month: "short",
                      year: "numeric",
                    })}
                  </time>
                </li>
              ))}
            </ul>
          </Section>
        </div>

        <div className="mt-6 grid grid-cols-[1.15fr_1fr] gap-6">
          <Section title="What the margin notes say" aside={`${notesTotal} notes, sorted by pattern`}>
            <Chart option={flagChart} h={340} />
            <p className="mt-5 text-sm leading-relaxed text-white/50">
              Each match stores the phrase that triggered it, so a wrong one is traceable to its
              cause rather than taken on faith. That is how the debut pattern below was caught
              scoring returns as first performances.
            </p>
          </Section>

          <div className="flex flex-col gap-6">
            <Section title="Checking the debut claims" aside="note against archive">
              <p className="text-[15px] leading-relaxed text-white/70">
                Of <span className="text-cream">{debutCheck.claims} notes</span> claiming a live
                debut, the performance history backs{" "}
                <span className="inline-flex items-center gap-1.5 text-cream">
                  <CheckCircle size={16} weight="fill" className="text-ember" />
                  {debutCheck.confirmed}
                </span>{" "}
                and contradicts{" "}
                <span className="inline-flex items-center gap-1.5 text-cream">
                  <Warning size={16} weight="fill" className="text-amber" />
                  {debutCheck.contradicted}
                </span>
                . Neither side is assumed right: the archive thins out before 2010, and a missing
                show looks exactly like a wrong note.
              </p>
              <table className="mt-5 w-full text-left text-[13px]">
                <caption className="sr-only">Debut claims contradicted by an earlier performance</caption>
                <thead>
                  <tr className="border-b border-white/10 text-white/40">
                    <th scope="col" className="pb-2 font-normal">Song</th>
                    <th scope="col" className="pb-2 text-right font-normal">Played earlier by</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/[0.06]">
                  {debutCheck.contradictions.map((row) => (
                    <tr key={row.song} className="transition-colors hover:bg-white/[0.03]">
                      <td className="truncate py-2 pr-4 text-white/75">{row.song}</td>
                      <td className="py-2 text-right text-white/45">{row.yearsEarlier} yr</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Section>

            <Section title="Songs dropped inside other songs" aside="teases and snippets">
              <ul className="flex flex-wrap gap-2">
                {teases.map((tease) => (
                  <li
                    key={tease.title}
                    className="inline-flex items-baseline gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 text-[13px] text-white/70"
                  >
                    {tease.title}
                    <span className="text-white/35">{tease.count}</span>
                  </li>
                ))}
              </ul>
            </Section>
          </div>
        </div>
      </div>
    </div>
  )
}
