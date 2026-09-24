import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowRight, House, MagnifyingGlass } from "@phosphor-icons/react";
import { pathOf, ROUTES, SIDES } from "./routes";

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  navigate: (path: string) => void;
}

interface Item {
  key: string;
  title: string;
  blurb: string;
  group: string;
  path: string;
  icon: typeof House;
  accent: "violet" | "ember" | "none";
}

const ITEMS: Item[] = [
  { key: "home", title: "Cover", blurb: "Back to the start", group: "Portal", path: "/", icon: House, accent: "none" },
  ...ROUTES.map((r) => ({
    key: `${r.side}/${r.slug}`,
    title: r.title,
    blurb: r.blurb,
    group: `${SIDES[r.side].sleeve} · ${SIDES[r.side].label}`,
    path: pathOf(r),
    icon: r.icon,
    accent: SIDES[r.side].accent,
  })),
];

// Subsequence match, scored so that consecutive hits and hits at word starts rank first.
function score(query: string, text: string): number {
  if (!query) return 1;
  const q = query.toLowerCase();
  const t = text.toLowerCase();
  let ti = 0;
  let total = 0;
  let run = 0;
  for (const ch of q) {
    const found = t.indexOf(ch, ti);
    if (found < 0) return 0;
    run = found === ti ? run + 1 : 0;
    total += 1 + run * 2 + (found === 0 || t[found - 1] === " " ? 3 : 0);
    ti = found + 1;
  }
  return total;
}

const iconTint = { violet: "text-violet-light", ember: "text-ember-light", none: "text-white/70" };

export default function CommandPalette({ open, onClose, navigate }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const results = useMemo(
    () =>
      ITEMS.map((item) => ({ item, s: Math.max(score(query, item.title) * 2, score(query, item.blurb)) }))
        .filter((r) => r.s > 0)
        .sort((x, y) => (query ? y.s - x.s : 0))
        .map((r) => r.item),
    [query],
  );

  useEffect(() => {
    if (open) {
      setQuery("");
      setCursor(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  useEffect(() => setCursor(0), [query]);

  const go = (item: Item | undefined) => {
    if (!item) return;
    navigate(item.path);
    onClose();
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-50 flex items-start justify-center px-4 pt-[14vh]"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
        >
          <div className="absolute inset-0 bg-ink/70 backdrop-blur-sm" onClick={onClose} />
          <motion.div
            role="dialog"
            aria-modal="true"
            aria-label="Jump to a page"
            className="relative w-full max-w-xl overflow-hidden rounded-2xl bg-[#140a18]/95 shadow-2xl shadow-black/60 ring-1 ring-white/10"
            initial={{ opacity: 0, y: -12, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 420, damping: 32 }}
            onKeyDown={(e) => {
              if (e.key === "Escape") onClose();
              else if (e.key === "ArrowDown") {
                e.preventDefault();
                setCursor((c) => Math.min(results.length - 1, c + 1));
              } else if (e.key === "ArrowUp") {
                e.preventDefault();
                setCursor((c) => Math.max(0, c - 1));
              } else if (e.key === "Enter") go(results[cursor]);
            }}
          >
            <div className="flex items-center gap-3 border-b border-white/[0.07] px-4">
              <MagnifyingGlass size={18} className="text-white/40" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search pages: encore, map, tempo..."
                className="h-14 w-full bg-transparent text-[15px] text-white outline-none placeholder:text-white/30"
                aria-controls="palette-results"
                aria-activedescendant={results[cursor] ? `palette-${results[cursor].key}` : undefined}
              />
              <kbd className="rounded bg-white/[0.08] px-1.5 py-0.5 font-mono text-[10px] text-white/45">Esc</kbd>
            </div>
            <ul id="palette-results" role="listbox" className="max-h-[52vh] overflow-y-auto p-2">
              {results.length === 0 && <li className="px-3 py-8 text-center text-sm text-white/40">No page matches that.</li>}
              {results.map((item, i) => {
                const Icon = item.icon;
                const active = i === cursor;
                const showGroup = !query && (i === 0 || results[i - 1].group !== item.group);
                return (
                  <li key={item.key} role="presentation">
                    {showGroup && <p className="px-3 pb-1 pt-3 text-[11px] text-white/35">{item.group}</p>}
                    <button
                      id={`palette-${item.key}`}
                      role="option"
                      aria-selected={active}
                      type="button"
                      onMouseMove={() => setCursor(i)}
                      onClick={() => go(item)}
                      className="relative flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left outline-none"
                    >
                      {active && (
                        <motion.span
                          layoutId="palette-cursor"
                          className="absolute inset-0 rounded-lg bg-white/[0.07]"
                          transition={{ type: "spring", stiffness: 500, damping: 40 }}
                        />
                      )}
                      <Icon size={18} className={`relative shrink-0 ${iconTint[item.accent]}`} />
                      <span className="relative min-w-0 flex-1">
                        <span className="block text-sm text-white">{item.title}</span>
                        <span className="block truncate text-xs text-white/40">{item.blurb}</span>
                      </span>
                      {query && <span className="relative text-[11px] text-white/30">{item.group}</span>}
                      <ArrowRight size={14} className={`relative shrink-0 transition-opacity ${active ? "text-white/60 opacity-100" : "opacity-0"}`} />
                    </button>
                  </li>
                );
              })}
            </ul>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
