import { AnimatePresence, motion, useMotionValue, useSpring } from "motion/react";
import { useState } from "react";
import { pathOf, photoOf, routesOf, SIDES, type RouteDef, type SideKey } from "./routes";

interface TrackListProps {
  side: SideKey;
  current?: RouteDef;
  onPick?: () => void;
  /** Row entry delay, so two lists opening together can cascade. */
  delay?: number;
  size?: "xl" | "lg";
}

const ease = [0.22, 1, 0.36, 1] as const;
const accentText = { violet: "text-violet-light", ember: "text-ember-light" };

// A tracklist set like the back of a sleeve, in poster type. Hovering a title dims the rest and
// floats that track's photograph under the cursor: the pictures earn their place as a reveal,
// not as a gallery.
export default function TrackList({ side, current, onPick, delay = 0, size = "xl" }: TrackListProps) {
  const s = SIDES[side];
  const tracks = routesOf(side);
  const [hover, setHover] = useState<RouteDef | null>(null);
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const sx = useSpring(x, { stiffness: 260, damping: 28, mass: 0.6 });
  const sy = useSpring(y, { stiffness: 260, damping: 28, mass: 0.6 });

  return (
    <div
      className="relative"
      onPointerMove={(e) => {
        const box = e.currentTarget.getBoundingClientRect();
        x.set(e.clientX - box.left);
        y.set(e.clientY - box.top);
      }}
      onPointerLeave={() => setHover(null)}
    >
      <p className={`mb-4 flex items-baseline gap-3 text-sm ${accentText[s.accent]}`}>
        <span className="font-serif text-2xl italic">{s.sleeve}</span>
        <span className="text-white/45">{s.label}</span>
      </p>

      <ol className="group/list relative z-10">
        {tracks.map((t, i) => {
          const active = current && current.slug === t.slug && current.side === t.side;
          return (
            <li key={t.slug} className="overflow-hidden border-t border-white/[0.08] last:border-b">
              <motion.a
                href={`#${pathOf(t)}`}
                onClick={onPick}
                onPointerEnter={() => {
                  setHover(t);
                  t.preload().catch(() => {});
                }}
                onFocus={() => setHover(t)}
                aria-current={active ? "page" : undefined}
                className="group/row relative flex items-baseline gap-4 py-2.5 outline-none transition-opacity duration-300 group-hover/list:opacity-35 hover:!opacity-100 focus-visible:!opacity-100 focus-visible:ring-2 focus-visible:ring-white/60 sm:gap-6"
                initial={{ y: "110%" }}
                animate={{ y: "0%" }}
                transition={{ duration: 0.35, delay: delay + i * 0.012, ease }}
              >
                <span className={`w-8 shrink-0 font-mono text-xs tabular-nums ${active ? accentText[s.accent] : "text-white/40"}`}>{t.code}</span>
                <span
                  className={`font-display font-medium leading-[1.05] tracking-tight transition-transform duration-500 ease-out group-hover/row:translate-x-3 ${
                    size === "xl" ? "text-[clamp(1.6rem,3.4vw,3.1rem)]" : "text-[clamp(1.35rem,2.4vw,2.2rem)]"
                  } ${active ? accentText[s.accent] : "text-white"}`}
                >
                  {t.title}
                </span>
                <span className="pointer-events-none absolute bottom-3 right-0 hidden max-w-[15rem] translate-y-1 text-right font-serif text-lg italic leading-tight text-white/0 transition-all duration-500 group-hover/row:translate-y-0 group-hover/row:text-white/70 lg:block">
                  {t.blurb}
                </span>
              </motion.a>
            </li>
          );
        })}
      </ol>

      {/* The photograph that follows the cursor */}
      <motion.div className="pointer-events-none absolute left-0 top-0 z-0 hidden md:block" style={{ x: sx, y: sy }}>
        <AnimatePresence>
          {hover && (
            <motion.img
              key={hover.slug}
              src={photoOf(hover).src}
              alt=""
              className="absolute max-w-none rounded-md object-cover shadow-2xl shadow-black/60"
              style={{ width: 260, height: 330, left: -130, top: -165 }}
              initial={{ opacity: 0, scale: 0.85, rotate: -6, filter: "blur(8px)" }}
              animate={{ opacity: 0.92, scale: 1, rotate: -3, filter: "blur(0px)" }}
              exit={{ opacity: 0, scale: 0.9, rotate: 2, filter: "blur(6px)" }}
              transition={{ duration: 0.45, ease }}
            />
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
