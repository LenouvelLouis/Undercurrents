import type { Accent } from "../lib/theme";

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

const activeText: Record<Accent, string> = {
  violet: "text-violet-light",
  ember: "text-ember-light",
};

const activeDot: Record<Accent, string> = {
  violet: "bg-violet",
  ember: "bg-ember",
};

// Styled like the back-sleeve tracklist of a record: a numbered row of titles rather
// than a grid of dashboard tiles.
export default function SubTabRow({ tabs, activeIndex, onChange, accent }: SubTabRowProps) {
  return (
    <div className="border-b border-white/5">
      <div className="mx-auto flex max-w-7xl flex-wrap gap-x-10 gap-y-3 px-8 py-5">
        {tabs.map((tab, i) => {
          const active = i === activeIndex;
          return (
            <button
              key={tab.index}
              onClick={() => onChange(i)}
              role="tab"
              aria-selected={active}
              className="group flex items-baseline gap-2"
            >
              <span
                className={`h-1.5 w-1.5 rounded-full transition-opacity ${active ? activeDot[accent] : "bg-white/20"}`}
              />
              <span className="font-mono text-xs text-white/30">{tab.index}</span>
              <span
                className={`font-display text-sm font-bold transition-colors ${
                  active ? activeText[accent] : "text-white/50 group-hover:text-white/80"
                }`}
              >
                {tab.title}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
