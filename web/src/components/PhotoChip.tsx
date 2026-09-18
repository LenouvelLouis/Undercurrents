import type { Accent } from "../lib/theme";

interface PhotoChipProps {
  src: string;
  alt: string;
  size?: number;
  accent?: Accent;
  className?: string;
  delay?: number;
}

const ringColor: Record<Accent, string> = {
  violet: "ring-violet/40",
  ember: "ring-ember/40",
};

// Small decorative photo accent (artist / album art) reused across pages that don't
// otherwise carry any imagery, so the interface reads as a real record-sleeve archive
// rather than plain data tiles. Purely visual: never a click target, never data-bearing.
export default function PhotoChip({ src, alt, size = 44, accent = "violet", className = "", delay = 0 }: PhotoChipProps) {
  return (
    <img
      src={src}
      alt={alt}
      title={alt}
      className={`anim-photo-chip shrink-0 rounded-xl object-cover shadow-lg shadow-black/40 ring-1 grayscale contrast-125 ${ringColor[accent]} ${className}`}
      style={{ width: size, height: size, animationDelay: `${delay}s` }}
    />
  );
}
