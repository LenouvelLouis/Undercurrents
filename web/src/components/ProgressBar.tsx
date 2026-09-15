import type { Accent } from "../lib/theme";
import { accentBg } from "../lib/theme";

export default function ProgressBar({ percentage, accent = "magenta" }: { percentage: number; accent?: Accent }) {
  const bg = accentBg[accent];
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
      <div className={`h-full rounded-full ${bg}`} style={{ width: `${Math.min(100, Math.max(0, percentage))}%` }} />
    </div>
  );
}
