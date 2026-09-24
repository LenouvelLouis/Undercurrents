import { AnimatePresence, motion } from "motion/react";
import { MagnifyingGlass } from "@phosphor-icons/react";
import Equalizer from "./Equalizer";
import Logo from "./Logo";
import SoundToggle from "./SoundToggle";
import { SIDES, type RouteDef } from "./routes";

interface HeaderProps {
  current?: RouteDef;
  menuOpen: boolean;
  onMenu: () => void;
  onSearch: () => void;
  onHome: () => void;
}

const accentText = { violet: "text-violet-light", ember: "text-ember-light" };

// Floating, not docked: three pills over the page. The middle one is the "now playing" readout,
// the right one opens the full tracklist.
export default function Header({ current, menuOpen, onMenu, onSearch, onHome }: HeaderProps) {
  const side = current ? SIDES[current.side] : null;
  return (
    <header className="pointer-events-none fixed inset-x-0 top-0 z-50 flex items-center justify-between gap-3 px-4 py-4 sm:px-8 sm:py-6">
      <button
        type="button"
        onClick={onHome}
        aria-label="Back to the cover"
        className="group pointer-events-auto flex items-center gap-2.5 rounded-full bg-ink/40 p-2 sm:pl-2.5 sm:pr-4 ring-1 ring-white/10 backdrop-blur-xl outline-none transition-colors hover:bg-ink/60 focus-visible:ring-2 focus-visible:ring-white/60"
      >
        <Logo className="h-6 w-6 transition-transform duration-700 group-hover:rotate-180" />
        <span className="hidden font-hero text-[13px] font-extrabold tracking-tight sm:inline">
          UNDER<span className="font-semibold text-white/45">CURRENTS</span>
        </span>
      </button>

      <AnimatePresence mode="popLayout">
        {current && side && !menuOpen && (
          <motion.button
            key={current.slug}
            type="button"
            onClick={onMenu}
            className="pointer-events-auto hidden items-center gap-3 rounded-full bg-ink/40 px-4 py-2 text-sm ring-1 ring-white/10 backdrop-blur-xl outline-none hover:bg-ink/60 focus-visible:ring-2 focus-visible:ring-white/60 md:flex"
            initial={{ opacity: 0, y: -12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            transition={{ duration: 0.35 }}
          >
            <Equalizer className={accentText[side.accent]} />
            <span className="text-white/45">Now playing</span>
            <span className="font-mono text-xs text-white/60">{current.code}</span>
            <span className="text-white">{current.title}</span>
          </motion.button>
        )}
      </AnimatePresence>

      <div className="pointer-events-auto flex items-center gap-2">
        <SoundToggle />
        <button
          type="button"
          onClick={onSearch}
          aria-label="Search pages"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-ink/40 ring-1 ring-white/10 backdrop-blur-xl outline-none transition-colors hover:bg-ink/60 focus-visible:ring-2 focus-visible:ring-white/60"
        >
          <MagnifyingGlass size={17} />
        </button>
        <button
          type="button"
          onClick={onMenu}
          aria-expanded={menuOpen}
          className="flex h-10 items-center gap-3 rounded-full bg-white px-4 text-sm font-medium text-ink outline-none transition-transform hover:scale-[1.03] focus-visible:ring-2 focus-visible:ring-violet-light focus-visible:ring-offset-2 focus-visible:ring-offset-ink"
        >
          <span className="relative block h-3 w-4">
            <motion.span
              className="absolute left-0 top-0.5 block h-[1.5px] w-4 bg-ink"
              animate={menuOpen ? { rotate: 45, y: 4 } : { rotate: 0, y: 0 }}
            />
            <motion.span
              className="absolute bottom-0.5 left-0 block h-[1.5px] w-4 bg-ink"
              animate={menuOpen ? { rotate: -45, y: -4 } : { rotate: 0, y: 0 }}
            />
          </span>
          {menuOpen ? "Close" : "Tracklist"}
        </button>
      </div>
    </header>
  );
}
