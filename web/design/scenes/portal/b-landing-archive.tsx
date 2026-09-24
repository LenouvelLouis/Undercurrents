import { ArrowRight, Crosshair, WaveTriangle } from "@phosphor-icons/react"
import { overview, sections } from "./_fixtures.ts"

export const meta = {
  title: "Landing - archive index",
  viewport: "laptop",
  theme: "dark",
  description:
    "Landing direction B: the archive index. The two halves of the product are the page, the photograph is evidence beside them rather than a backdrop behind everything.",
}

export default function LandingArchive() {
  return (
    <div className="min-h-screen bg-bg font-body text-white [font-variant-numeric:tabular-nums]">
      <div className="mx-auto max-w-[1180px] px-12 py-14">
        <header className="flex items-end justify-between gap-10 border-b border-white/10 pb-10">
          <div>
            <h1 className="font-hero text-6xl leading-[0.92] tracking-tight">
              UNDER<span className="text-white/45">CURRENTS</span>
            </h1>
            <p className="mt-5 max-w-lg text-[15px] leading-relaxed text-white/65">
              An archive of {overview.concerts} Tame Impala concerts across {overview.venues} venues
              and {overview.countries} countries, and the models that try to guess what comes next.
            </p>
          </div>
          <p className="shrink-0 pb-2 text-right text-sm leading-relaxed text-white/40">
            {overview.yearsStart} to {overview.yearsEnd}
            <br />
            {overview.clusters} setlist clusters
          </p>
        </header>

        <div className="mt-10 grid grid-cols-2 gap-6">
          {sections.map((section) => {
            const isPrediction = section.key === "predictions"
            const Icon = isPrediction ? Crosshair : WaveTriangle
            return (
              <button
                key={section.key}
                type="button"
                data-goto="portal/nav"
                className={`group relative overflow-hidden rounded-2xl border p-8 text-left outline-none transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-bg ${
                  isPrediction
                    ? "border-violet/30 bg-violet-dark/15 hover:border-violet/60 focus-visible:ring-violet-light"
                    : "border-ember/30 bg-ember-dark/15 hover:border-ember/60 focus-visible:ring-ember-light"
                }`}
              >
                <Icon
                  size={26}
                  weight="regular"
                  className={isPrediction ? "text-violet-light" : "text-ember-light"}
                />
                <h2 className="mt-5 font-display text-2xl font-semibold tracking-tight">
                  {section.label}
                </h2>
                <p className="mt-2 max-w-sm text-sm leading-relaxed text-white/55">{section.blurb}</p>
                <p className="mt-6 flex items-center gap-2 text-sm text-white/45">
                  {section.pages.length} pages
                  <ArrowRight
                    size={15}
                    weight="bold"
                    className="transition-transform group-hover:translate-x-1"
                  />
                </p>
              </button>
            )
          })}
        </div>

        <figure className="mt-10 overflow-hidden rounded-2xl border border-white/10">
          <div className="relative h-52">
            <img
              src="/src/assets/concert/concert-silhouette-lasers.jpg"
              alt="Silhouettes against the lasers during a show"
              className="h-full w-full object-cover"
              style={{ objectPosition: "center 40%" }}
            />
            <div className="grain-overlay" />
          </div>
          <figcaption className="px-6 py-4 text-sm text-white/40">
            Silhouettes against the lasers. The archive holds the photographs as well as the
            numbers, and both are evidence.
          </figcaption>
        </figure>
      </div>
    </div>
  )
}
