import type { Accent } from "../lib/theme";
import { accentBgTint, accentBorder } from "../lib/theme";

interface SubTab {
  index: string;
  title: string;
}

interface SubTabRowProps {
  tabs: SubTab[];
  activeIndex: number;
  onChange: (index: number) => void;
  accent: Accent;
}

export default function SubTabRow({ tabs, activeIndex, onChange, accent }: SubTabRowProps) {
  return (
    <div className="grid grid-cols-5 gap-3 px-8">
      {tabs.map((tab, i) => {
        const active = i === activeIndex;
        return (
          <button
            key={tab.index}
            onClick={() => onChange(i)}
            role="tab"
            aria-selected={active}
            className={`rounded-lg border p-4 text-left transition-colors ${
              active
                ? `${accentBorder[accent]} ${accentBgTint[accent]}`
                : "border-white/10 bg-white/[0.02] hover:border-white/20"
            }`}
          >
            <div className="font-mono text-xs text-white/40">{tab.index}</div>
            <div className="font-display font-bold text-white">{tab.title}</div>
          </button>
        );
      })}
    </div>
  );
}
