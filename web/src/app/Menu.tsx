import { AnimatePresence, motion } from "motion/react";
import { useEffect } from "react";
import TrackList from "./TrackList";
import Waveform from "./Waveform";
import type { RouteDef } from "./routes";

interface MenuProps {
  open: boolean;
  current?: RouteDef;
  onClose: () => void;
  onSearch: () => void;
}

const ease = [0.76, 0, 0.24, 1] as const;

// The whole site on one sleeve: both sides' tracklists full screen, dropped over the page like
// a curtain. Esc or picking a track lifts it.
export default function Menu({ open, current, onClose, onSearch }: MenuProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          role="dialog"
          aria-modal="true"
          aria-label="Tracklist"
          className="fixed inset-0 z-40 overflow-y-auto bg-ink/80 backdrop-blur-2xl"
          initial={{ clipPath: "inset(0 0 100% 0)" }}
          animate={{ clipPath: "inset(0 0 0% 0)" }}
          exit={{ clipPath: "inset(100% 0 0 0)" }}
          transition={{ duration: 0.8, ease }}
        >
          <div className="mx-auto grid max-w-[1500px] gap-14 px-6 pb-20 pt-28 sm:px-12 lg:grid-cols-2 lg:gap-20">
            <TrackList side="predictions" current={current} onPick={onClose} delay={0.25} />
            <TrackList side="analysis" current={current} onPick={onClose} delay={0.35} size="lg" />
          </div>
          <Waveform className="h-24" traces={3} />
          <motion.div
            className="mx-auto flex max-w-[1500px] items-center justify-between px-6 pb-10 text-sm text-white/45 sm:px-12"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1, transition: { delay: 0.8 } }}
          >
            <span>Esc to close</span>
            <button
              type="button"
              onClick={() => {
                onClose();
                onSearch();
              }}
              className="rounded-full px-3 py-1 outline-none ring-1 ring-white/15 hover:text-white focus-visible:ring-2 focus-visible:ring-white/60"
            >
              Search pages · Ctrl K
            </button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
