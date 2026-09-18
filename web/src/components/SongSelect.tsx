import { useEffect, useRef, useState } from "react";
import type { Accent } from "../lib/theme";
import type { Song } from "../lib/types";

interface SongSelectProps {
  songs: Song[];
  value: Song | null;
  onChange: (song: Song) => void;
  accent?: Accent;
}

const focusRing: Record<Accent, string> = {
  violet: "focus:border-violet",
  ember: "focus:border-ember",
};

const activeBg: Record<Accent, string> = {
  violet: "bg-violet/15 text-violet-light",
  ember: "bg-ember/15 text-ember-light",
};

// A custom-styled dropdown so song pickers match the rest of the interface: a native
// <select>'s open option list is drawn by the OS and ignores almost all CSS, which reads
// as a jarring plain white box against the app's dark, bespoke design.
export default function SongSelect({ songs, value, onChange, accent = "ember" }: SongSelectProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`flex w-full items-center justify-between rounded-lg border border-white/20 bg-white/5 px-4 py-2 text-left text-white outline-none ${focusRing[accent]}`}
      >
        <span className="truncate">{value?.name ?? "Select a song…"}</span>
        <svg width="12" height="12" viewBox="0 0 12 12" className={`shrink-0 transition-transform ${open ? "rotate-180" : ""}`}>
          <path d="M2 4 L6 8 L10 4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>
      {open && (
        <ul className="absolute z-20 mt-2 max-h-64 w-full overflow-y-auto rounded-lg border border-white/10 bg-bg shadow-xl">
          {songs.map((song) => (
            <li
              key={song.id}
              onClick={() => {
                onChange(song);
                setOpen(false);
              }}
              className={`cursor-pointer px-4 py-2 text-sm transition-colors hover:bg-white/10 ${
                song.id === value?.id ? activeBg[accent] : "text-white/80"
              }`}
            >
              {song.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
