import { AnimatePresence, motion } from "motion/react";
import { Suspense, useEffect } from "react";
import { ArrowUpRight } from "@phosphor-icons/react";
import { pathOf, photoOf, routesOf, SIDES, type RouteDef } from "./routes";
import Waveform from "./Waveform";

interface ShellProps {
  route: RouteDef;
  navigate: (path: string) => void;
}

const ease = [0.76, 0, 0.24, 1] as const;
const soft = [0.22, 1, 0.36, 1] as const;
const accentText = { violet: "text-violet-light", ember: "text-ember-light" };
const accentFill = { violet: "from-violet via-violet-light to-cream", ember: "from-ember via-ember-light to-amber-light" };
const curtainTint = { violet: "from-[#2a0838] via-ink to-[#12041a]", ember: "from-[#3a0f08] via-ink to-[#1a0806]" };

function isTyping(target: EventTarget | null) {
  const el = target as HTMLElement | null;
  return !!el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.tagName === "SELECT" || el.isContentEditable);
}

export default function Shell({ route, navigate }: ShellProps) {
  const side = SIDES[route.side];
  const tracks = routesOf(route.side);
  const index = tracks.findIndex((t) => t.slug === route.slug);
  const prev = tracks[index - 1];
  const next = tracks[index + 1] ?? routesOf(route.side === "predictions" ? "analysis" : "predictions")[0];

  // "[" and "]" skip tracks, like the buttons on a deck.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (isTyping(e.target) || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "[" && prev) navigate(pathOf(prev));
      if (e.key === "]" && next) navigate(pathOf(next));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [prev, next, navigate]);

  const Page = route.Component;
  const key = pathOf(route);

  return (
    <>
      {/* Curtain: sweeps up over the old page, holds on the track code, lifts off the new one */}
      <AnimatePresence initial={false}>
        <motion.div
          key={key}
          aria-hidden
          className={`pointer-events-none fixed inset-0 z-[45] flex items-end bg-gradient-to-br ${curtainTint[side.accent]} px-6 pb-12 sm:px-12`}
          initial={{ y: "100%" }}
          animate={{ y: ["100%", "0%", "0%", "-100%"] }}
          transition={{ duration: 1.25, times: [0, 0.34, 0.62, 1], ease }}
          onAnimationStart={() => window.setTimeout(() => window.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior }), 420)}
        >
          <Waveform className="absolute inset-x-0 top-1/3 h-40" traces={3} from={side.accent === "violet" ? "#e2a6ff" : "#ff9270"} to={side.accent === "violet" ? "#a531d6" : "#f0c581"} />
          <div className="relative">
            <p className={`font-mono text-sm ${accentText[side.accent]}`}>
              {side.sleeve}, track {route.code.slice(1)}
            </p>
            <p className="chroma mt-2 font-hero text-[clamp(2.5rem,9vw,8rem)] font-extrabold uppercase leading-[0.85] text-white">{route.title}</p>
          </div>
        </motion.div>
      </AnimatePresence>

      <main className="relative mx-auto max-w-[1400px] px-5 pb-24 pt-28 sm:px-10 sm:pt-36">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={key}
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0, transition: { duration: 0.8, delay: 0.55, ease: soft } }}
            exit={{ opacity: 0, transition: { duration: 0.35 } }}
          >
            {/* Oversized outline track code behind the page title */}
            <div aria-hidden className="pointer-events-none absolute right-0 top-16 -z-[1] select-none sm:right-6">
              <span className="text-outline font-hero text-[clamp(7rem,22vw,20rem)] font-extrabold leading-none">{route.code}</span>
            </div>
            <p className={`mb-3 flex items-baseline gap-3 text-sm ${accentText[side.accent]}`}>
              <span className="font-serif text-xl italic">{side.sleeve}</span>
              <span className="text-white/45">{route.blurb}</span>
            </p>

            <Suspense fallback={<div className="h-[60vh]" aria-busy="true" />}>
              <Page />
            </Suspense>

            <Waveform className="mt-24 h-20" traces={2} from={side.accent === "violet" ? "#e2a6ff" : "#ff9270"} to={side.accent === "violet" ? "#ff9270" : "#e2a6ff"} amplitude={0.3} />

            {/* Next track: the whole width is the link */}
            <a
              href={`#${pathOf(next)}`}
              className="group relative mt-6 block overflow-hidden pt-4 outline-none focus-visible:ring-2 focus-visible:ring-white/60"
            >
              <span className="flex items-center justify-between text-sm text-white/45">
                <span>
                  Next track <span className="ml-2 font-mono text-xs">{next.code}</span>
                </span>
                <ArrowUpRight size={22} className="transition-transform duration-500 group-hover:-translate-y-1 group-hover:translate-x-1 group-hover:text-white" />
              </span>
              <span className="relative mt-3 block font-hero text-[clamp(2.6rem,8vw,7.5rem)] font-extrabold uppercase leading-[0.88] tracking-tight">
                <span className="text-white/15 transition-colors duration-500 group-hover:text-transparent">{next.title}</span>
                <span
                  className={`absolute inset-0 bg-gradient-to-r ${accentFill[SIDES[next.side].accent]} bg-clip-text text-transparent [clip-path:inset(0_100%_0_0)] transition-[clip-path] duration-700 ease-out group-hover:[clip-path:inset(0_0%_0_0)]`}
                >
                  {next.title}
                </span>
              </span>
              <img
                src={photoOf(next).src}
                alt=""
                className="pointer-events-none absolute right-10 top-4 hidden h-40 w-32 rotate-6 rounded-md object-cover opacity-0 shadow-2xl transition-all duration-700 group-hover:rotate-3 group-hover:opacity-90 md:block"
              />
            </a>
          </motion.div>
        </AnimatePresence>
      </main>
    </>
  );
}
