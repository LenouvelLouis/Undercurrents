import type { Overview } from "../lib/types";

interface LandingProps {
  overview: Overview | null;
  onExplore: () => void;
}

export default function Landing({ overview, onExplore }: LandingProps) {
  const stats = overview
    ? [
        { value: String(overview.concerts_logged), label: "concerts logged" },
        { value: `${overview.years_end - overview.years_start}`, label: `years, ${overview.years_start}-${overview.years_end}` },
        { value: String(overview.venues_mapped), label: "venues mapped" },
        { value: String(overview.countries), label: "countries" },
        { value: `${Math.round((overview.setlist_accuracy ?? 0) * 100)}%`, label: "setlist accuracy" },
        { value: String(overview.setlist_clusters), label: "setlist clusters" },
      ]
    : [];

  return (
    <div className="mx-auto flex min-h-screen max-w-5xl flex-col justify-center px-8">
      <p className="font-mono text-xs tracking-[0.3em] text-magenta-light">TAME IMPALA TOUR INTELLIGENCE</p>
      <h1 className="mt-4 font-display text-7xl leading-none">
        <div className="font-bold text-white">UNDER</div>
        <div className="font-medium text-white/50">CURRENTS</div>
      </h1>
      <p className="mt-6 max-w-xl text-lg text-white/70">
        Eighteen years of real setlists, venues and tours, run through predictive models —
        probabilities and honest uncertainty, not a single guess.
      </p>
      <button
        onClick={onExplore}
        className="mt-8 w-fit rounded-full bg-gradient-to-r from-magenta to-magenta-light px-6 py-3 font-medium text-black"
      >
        Explore the predictions →
      </button>
      {stats.length > 0 && (
        <div className="mt-16 grid grid-cols-3 gap-6 border-t border-white/10 pt-8 sm:grid-cols-6">
          {stats.map((stat) => (
            <div key={stat.label}>
              <div className="font-display text-3xl font-bold text-white">{stat.value}</div>
              <div className="font-mono text-xs text-white/40">{stat.label}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
