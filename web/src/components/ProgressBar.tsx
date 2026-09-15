import type { Accent } from "../lib/theme";

const gradientClass: Record<Accent, string> = {
  violet: "bg-gradient-to-r from-violet-dark via-violet to-violet-light",
  ember: "bg-gradient-to-r from-ember-dark via-ember to-ember-light",
};

export default function ProgressBar({ percentage, accent = "violet" }: { percentage: number; accent?: Accent }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
      <div
        className={`h-full rounded-full ${gradientClass[accent]}`}
        style={{ width: `${Math.min(100, Math.max(0, percentage))}%` }}
      />
    </div>
  );
}
