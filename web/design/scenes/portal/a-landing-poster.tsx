import { ArrowRight } from "@phosphor-icons/react"
import { overview } from "./_fixtures.ts"

export const meta = {
  title: "Landing - poster",
  viewport: "laptop",
  theme: "dark",
  description:
    "Landing direction A: the record sleeve. One photograph carries the page, the figures sit under it as a quiet strip rather than as oversized stat heroes.",
}

const figures = [
  { value: overview.concerts, label: "concerts on record" },
  { value: `${overview.yearsEnd - overview.yearsStart}`, label: `years, ${overview.yearsStart} to ${overview.yearsEnd}` },
  { value: overview.venues, label: "venues" },
  { value: overview.countries, label: "countries" },
]

export default function LandingPoster() {
  return (
    <div className="min-h-screen bg-bg font-body text-white [font-variant-numeric:tabular-nums]">
      <section className="relative h-[560px] overflow-hidden border-b border-white/10">
        <img
          src="/src/assets/concert/concert-guitarist-confetti.jpg"
          alt="Kevin Parker playing guitar as confetti falls across the stage"
          className="absolute inset-0 h-full w-full object-cover"
          style={{ objectPosition: "center 45%" }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-bg via-bg/60 to-bg/10" />
        <div className="absolute inset-0 bg-gradient-to-r from-bg/90 via-bg/25 to-transparent" />
        <div className="grain-overlay" />

        <div className="absolute inset-x-0 bottom-0 px-12 pb-12">
          <h1 className="font-hero text-7xl leading-[0.9] tracking-tight text-balance">
            UNDER
            <br />
            <span className="text-white/50">CURRENTS</span>
          </h1>
          <p className="mt-5 max-w-md text-[15px] leading-relaxed text-white/70">
            Eighteen years of real setlists, venues and tours, run through models that always
            show their score against the simplest thing that could have beaten them.
          </p>
          <button
            type="button"
            className="group mt-7 inline-flex items-center gap-2 rounded-full bg-violet px-5 py-3 text-[15px] font-medium text-ink shadow-glow-violet outline-none transition-transform hover:scale-[1.02] focus-visible:ring-2 focus-visible:ring-violet-light focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
            data-goto="portal/nav"
          >
            Explore the predictions
            <ArrowRight size={17} weight="bold" className="transition-transform group-hover:translate-x-0.5" />
          </button>
        </div>
      </section>

      {/* The figures as a quiet strip, not four oversized numbers with tiny labels. They are
          context for the sentence above, not the hero of the page. */}
      <dl className="mx-auto flex max-w-[1180px] flex-wrap gap-x-12 gap-y-4 px-12 py-8">
        {figures.map((figure) => (
          <div key={figure.label} className="flex items-baseline gap-2">
            <dt className="sr-only">{figure.label}</dt>
            <dd className="font-display text-xl font-semibold text-cream">{figure.value}</dd>
            <span aria-hidden className="text-sm text-white/45">{figure.label}</span>
          </div>
        ))}
      </dl>
    </div>
  )
}
