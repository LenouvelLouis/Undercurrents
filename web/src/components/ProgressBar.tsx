import type { Accent } from "../lib/theme";

const fill: Record<Accent, string> = {
  violet: "bg-gradient-to-r from-violet/70 to-violet-light",
  ember: "bg-gradient-to-r from-ember/70 to-ember-light",
};

// A meter, not a decoration: thin track, the value grows in from the left on mount.
export default function ProgressBar({ percentage, accent = "violet" }: { percentage: number; accent?: Accent }) {
  const value = Math.min(100, Math.max(0, percentage));
  return (
    <div
      className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.07]"
      role="meter"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(value)}
    >
      <div className={`anim-width-in h-full rounded-full ${fill[accent]}`} style={{ width: `${value}%` }} />
    </div>
  );
}
