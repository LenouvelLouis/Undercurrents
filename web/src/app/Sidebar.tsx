import { AnimatePresence, LayoutGroup, motion } from "motion/react";
import { MagnifyingGlass } from "@phosphor-icons/react";
import type { Overview } from "../lib/types";
import Equalizer from "./Equalizer";
import Logo from "./Logo";
import { pathOf, routesOf, SIDES, type RouteDef, type SideKey } from "./routes";

interface SidebarProps {
  current: RouteDef;
  overview: Overview | null;
  navigate: (path: string) => void;
  onSearch: () => void;
}

const ease = [0.22, 1, 0.36, 1] as const;

const accentText = { violet: "text-violet-light", ember: "text-ember-light" };
const accentBar = { violet: "bg-violet-light", ember: "bg-ember-light" };
const accentPill = { violet: "bg-violet/20 ring-violet/40", ember: "bg-ember/20 ring-ember/40" };

// The navigation is a record sleeve: two sides, each a tracklist. The side switch and the
// active row both use a shared-layout highlight, so the selection glides to its new place
// instead of blinking there.
export default function Sidebar({ current, overview, navigate, onSearch }: SidebarProps) {
  const side = SIDES[current.side];
  const tracks = routesOf(current.side);
  const isMac = typeof navigator !== "undefined" && /Mac/i.test(navigator.platform);

  return (
    <div className="flex h-full flex-col">
      <button
        type="button"
        onClick={() => navigate("/")}
        className="group mx-5 mt-6 flex items-center gap-3 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-white/60 focus-visible:ring-offset-4 focus-visible:ring-offset-ink"
        aria-label="Back to the cover"
      >
        <Logo className="h-7 w-7 transition-transform duration-500 group-hover:rotate-90" />
        <span className="font-hero text-[15px] tracking-tight">
          <span className="font-extrabold text-white">UNDER</span>
          <span className="font-semibold text-white/45">CURRENTS</span>
        </span>
      </button>

      {/* Side switch */}
      <LayoutGroup id="sides">
        <div role="tablist" aria-label="Side" className="mx-4 mt-8 grid grid-cols-2 gap-1 rounded-xl bg-white/[0.04] p-1 ring-1 ring-white/[0.06]">
          {(Object.keys(SIDES) as SideKey[]).map((key) => {
            const s = SIDES[key];
            const active = key === current.side;
            return (
              <button
                key={key}
                role="tab"
                aria-selected={active}
                type="button"
                onClick={() => !active && navigate(pathOf(routesOf(key)[0]))}
                className="relative rounded-lg px-3 py-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-white/60"
              >
                {active && (
                  <motion.span
                    layoutId="side-pill"
                    className={`absolute inset-0 rounded-lg ring-1 ${accentPill[s.accent]}`}
                    transition={{ type: "spring", stiffness: 380, damping: 32 }}
                  />
                )}
                <span className="relative block text-[11px] text-white/45">{s.sleeve}</span>
                <span className={`relative block text-sm font-medium transition-colors ${active ? accentText[s.accent] : "text-white/60"}`}>
                  {s.label}
                </span>
              </button>
            );
          })}
        </div>
      </LayoutGroup>

      {/* Tracklist */}
      <nav aria-label={`${side.sleeve}, ${side.label}`} className="relative mt-6 min-h-0 flex-1 overflow-y-auto px-3 pb-4">
        <AnimatePresence mode="wait" initial={false}>
          <motion.ul
            key={current.side}
            className="space-y-0.5"
            initial="hidden"
            animate="show"
            exit="gone"
            variants={{
              hidden: {},
              show: { transition: { staggerChildren: 0.03 } },
              gone: { opacity: 0, x: -12, transition: { duration: 0.15 } },
            }}
          >
            <LayoutGroup id={`tracks-${current.side}`}>
              {tracks.map((track) => {
                const active = track.slug === current.slug;
                const Icon = track.icon;
                return (
                  <motion.li
                    key={track.slug}
                    variants={{ hidden: { opacity: 0, x: -10 }, show: { opacity: 1, x: 0, transition: { duration: 0.35, ease } } }}
                  >
                    <a
                      href={`#${pathOf(track)}`}
                      aria-current={active ? "page" : undefined}
                      title={track.blurb}
                      className="group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-white/50"
                    >
                      {active && (
                        <motion.span
                          layoutId="track-highlight"
                          className="absolute inset-0 rounded-lg bg-white/[0.07]"
                          transition={{ type: "spring", stiffness: 420, damping: 36 }}
                        >
                          <span className={`absolute left-0 top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-full ${accentBar[side.accent]}`} />
                        </motion.span>
                      )}
                      {/* Leading slot: the page icon, swapped for the equalizer on the page
                          that is playing. No track numbers: the order carries no meaning. */}
                      <span className="relative flex w-5 shrink-0 items-center justify-center">
                        {active ? (
                          <Equalizer className={accentText[side.accent]} />
                        ) : (
                          <Icon size={16} className="text-white/40 transition-colors group-hover:text-white/80" />
                        )}
                      </span>
                      <span className={`relative truncate transition-colors ${active ? "text-white" : "text-white/55 group-hover:text-white/90"}`}>
                        {track.title}
                      </span>
                    </a>
                  </motion.li>
                );
              })}
            </LayoutGroup>
          </motion.ul>
        </AnimatePresence>
      </nav>

      <div className="border-t border-white/[0.06] p-4">
        <button
          type="button"
          onClick={onSearch}
          className="flex w-full items-center gap-2 rounded-lg bg-white/[0.04] px-3 py-2 text-sm text-white/50 ring-1 ring-white/[0.06] outline-none transition-colors hover:bg-white/[0.07] hover:text-white/80 focus-visible:ring-2 focus-visible:ring-white/50"
        >
          <MagnifyingGlass size={15} />
          Jump to a page
          <kbd className="ml-auto rounded bg-white/[0.08] px-1.5 py-0.5 font-mono text-[10px] text-white/50">{isMac ? "⌘" : "Ctrl"} K</kbd>
        </button>
        {overview && (
          <p className="mt-3 px-1 text-[11px] leading-relaxed tabular-nums text-white/35">
            {overview.concerts_logged} shows, {overview.venues_mapped} venues, {overview.countries} countries,{" "}
            {overview.years_start} to {overview.years_end}
          </p>
        )}
      </div>
    </div>
  );
}
