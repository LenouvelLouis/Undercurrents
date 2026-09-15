import type { Accent } from "../lib/theme";

interface TopNavProps {
  activeTab: "predictions" | "analysis";
  onTabChange: (tab: "predictions" | "analysis") => void;
  shows: number;
  yearsStart: number;
  yearsEnd: number;
}

const TABS: { key: "predictions" | "analysis"; label: string; accent: Accent }[] = [
  { key: "predictions", label: "Predictions", accent: "violet" },
  { key: "analysis", label: "Data Analysis", accent: "ember" },
];

const underlineColor: Record<Accent, string> = {
  violet: "bg-violet",
  ember: "bg-ember",
};

const textColor: Record<Accent, string> = {
  violet: "text-violet-light",
  ember: "text-ember-light",
};

export default function TopNav({ activeTab, onTabChange, shows, yearsStart, yearsEnd }: TopNavProps) {
  return (
    <header className="sticky top-0 z-20 border-b border-white/5 bg-ink/70 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-8 py-5">
        <div className="flex items-center gap-3">
          <svg width="26" height="26" viewBox="0 0 28 28">
            <defs>
              <linearGradient id="logo-grad" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="28" y2="28">
                <stop offset="0%" stopColor="#e2a6ff" />
                <stop offset="100%" stopColor="#ff9270" />
              </linearGradient>
            </defs>
            <circle cx="14" cy="14" r="2" fill="url(#logo-grad)" />
            {Array.from({ length: 8 }, (_, i) => {
              const angle = (i / 8) * Math.PI * 2;
              const x = 14 + Math.cos(angle) * 10;
              const y = 14 + Math.sin(angle) * 10;
              return <circle key={i} cx={x} cy={y} r="1.5" fill="url(#logo-grad)" opacity={0.85} />;
            })}
          </svg>
          <span className="font-hero text-lg tracking-tight">
            <span className="font-extrabold text-white">UNDER</span>
            <span className="font-semibold text-white/50">CURRENTS</span>
          </span>
        </div>

        <nav className="flex items-center gap-8">
          {TABS.map((tab) => {
            const active = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => onTabChange(tab.key)}
                aria-current={active ? "page" : undefined}
                className="group relative py-2 font-display text-sm font-medium"
              >
                <span className={active ? textColor[tab.accent] : "text-white/50 group-hover:text-white/80"}>
                  {tab.label}
                </span>
                <span
                  className={`absolute -bottom-[1px] left-0 h-[2px] w-full origin-left rounded-full transition-transform duration-200 ${
                    active ? `${underlineColor[tab.accent]} scale-x-100` : "scale-x-0 bg-white/40 group-hover:scale-x-100"
                  }`}
                />
              </button>
            );
          })}
        </nav>

        <span className="font-mono text-xs tracking-widest text-white/40">
          UC-{String(shows).padStart(3, "0")} · {yearsStart}–{yearsEnd}
        </span>
      </div>
    </header>
  );
}
