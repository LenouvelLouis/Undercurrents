import type { Accent } from "../lib/theme";

interface TopNavProps {
  activeTab: "predictions" | "analysis";
  onTabChange: (tab: "predictions" | "analysis") => void;
  shows: number;
  yearsStart: number;
  yearsEnd: number;
}

function pillClasses(active: boolean, accent: Accent) {
  if (!active) return "px-5 py-2 rounded-full text-white/60 hover:text-white transition-colors";
  const bg = accent === "magenta" ? "bg-magenta" : "bg-teal";
  return `px-5 py-2 rounded-full font-medium text-black ${bg}`;
}

export default function TopNav({ activeTab, onTabChange, shows, yearsStart, yearsEnd }: TopNavProps) {
  return (
    <header className="flex items-center justify-between px-8 py-6">
      <div className="flex items-center gap-3">
        <svg width="28" height="28" viewBox="0 0 28 28" className="text-magenta">
          <circle cx="14" cy="14" r="2" fill="currentColor" />
          {Array.from({ length: 8 }, (_, i) => {
            const angle = (i / 8) * Math.PI * 2;
            const x = 14 + Math.cos(angle) * 10;
            const y = 14 + Math.sin(angle) * 10;
            return <circle key={i} cx={x} cy={y} r="1.5" fill="currentColor" opacity={0.7} />;
          })}
        </svg>
        <span className="font-display text-xl">
          <span className="font-bold text-white">UNDER</span>
          <span className="font-medium text-white/60">CURRENTS</span>
        </span>
      </div>
      <div className="flex items-center gap-6">
        <nav className="flex gap-2 rounded-full bg-white/5 p-1">
          <button
            className={pillClasses(activeTab === "predictions", "magenta")}
            onClick={() => onTabChange("predictions")}
            aria-current={activeTab === "predictions" ? "page" : undefined}
          >
            Predictions
          </button>
          <button
            className={pillClasses(activeTab === "analysis", "teal")}
            onClick={() => onTabChange("analysis")}
            aria-current={activeTab === "analysis" ? "page" : undefined}
          >
            Data Analysis
          </button>
        </nav>
        <span className="font-mono text-xs tracking-widest text-white/40">
          {shows} SHOWS · {yearsStart}–{yearsEnd}
        </span>
      </div>
    </header>
  );
}
