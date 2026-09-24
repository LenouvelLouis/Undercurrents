import { ChartLineUp, Crosshair, MagnifyingGlass } from "@phosphor-icons/react"
import { sections } from "./_fixtures.ts"

export const meta = {
  title: "Navigation",
  viewport: "laptop",
  theme: "dark",
  description:
    "The two-section tab system, rebuilt without the 01-13 numbering the page order never justified, and with the section accent doing the work the numbers were doing.",
}

export default function Nav() {
  const active = sections[1]

  return (
    <div className="min-h-screen bg-bg font-body text-white">
      <header className="sticky top-0 z-10 border-b border-white/10 bg-bg/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-[1180px] items-center gap-8 px-10 py-4">
          <a
            href="#"
            className="font-hero text-lg tracking-tight outline-none focus-visible:ring-2 focus-visible:ring-white/60 focus-visible:ring-offset-4 focus-visible:ring-offset-bg"
          >
            UNDER<span className="text-white/45">CURRENTS</span>
          </a>

          <nav aria-label="Sections" className="flex items-center gap-1">
            {sections.map((section) => {
              const isActive = section.key === active.key
              const Icon = section.key === "predictions" ? Crosshair : ChartLineUp
              return (
                <button
                  key={section.key}
                  type="button"
                  aria-current={isActive ? "page" : undefined}
                  className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-bg ${
                    isActive
                      ? section.accent === "violet"
                        ? "bg-violet/15 text-violet-light focus-visible:ring-violet-light"
                        : "bg-ember/15 text-ember-light focus-visible:ring-ember-light"
                      : "text-white/55 hover:bg-white/[0.06] hover:text-white focus-visible:ring-white/60"
                  }`}
                >
                  <Icon size={17} weight={isActive ? "fill" : "regular"} />
                  {section.label}
                </button>
              )
            })}
          </nav>

          <label className="ml-auto flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3.5 py-2 text-sm text-white/45 transition-colors focus-within:border-white/30 hover:border-white/20">
            <MagnifyingGlass size={16} />
            <input
              type="search"
              placeholder="Find a song, a venue, a night"
              className="w-56 bg-transparent text-white placeholder:text-white/35 outline-none"
            />
          </label>
        </div>

        {/* The page row. Previously every entry carried a 01..13 prefix; the order of these
            pages means nothing, so the numbers were decoration that read as a sequence. */}
        <div className="mx-auto max-w-[1180px] px-10">
          <div className="flex flex-wrap gap-x-1 gap-y-1 pb-3">
            {active.pages.map((page, i) => (
              <button
                key={page}
                type="button"
                aria-current={i === 11 ? "page" : undefined}
                className={`rounded-lg px-3 py-1.5 text-[13px] outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ember-light focus-visible:ring-offset-2 focus-visible:ring-offset-bg ${
                  i === 11
                    ? "bg-white/[0.08] text-white"
                    : "text-white/45 hover:bg-white/[0.05] hover:text-white/85"
                }`}
              >
                {page}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1180px] px-10 py-12">
        <p className="max-w-lg text-[15px] leading-relaxed text-white/45">
          The section accent, violet for prediction and ember for the record, is the only thing
          telling you which half of the product you are in. It replaces a numbered index that
          implied an order the pages do not have.
        </p>
      </main>
    </div>
  )
}
