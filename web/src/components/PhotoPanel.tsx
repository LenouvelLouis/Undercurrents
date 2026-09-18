import type { CSSProperties } from "react";
import type { Accent } from "../lib/theme";
import type { Photo } from "../lib/photos";

interface PhotoPanelProps {
  photo: Photo;
  accent?: Accent;
  /** Small mono tag in the top corner, e.g. "FROM THE ARCHIVE" or a year. */
  tag?: string;
  className?: string;
  style?: CSSProperties;
  /** Focal point for the crop, since a tall photo in a wide slot loses its edges. */
  focus?: string;
}

const ringClass: Record<Accent, string> = {
  violet: "border-violet/30 hover:border-violet/70",
  ember: "border-ember/30 hover:border-ember/70",
};

const glowClass: Record<Accent, string> = {
  violet: "from-violet/30",
  ember: "from-ember/30",
};

const dotClass: Record<Accent, string> = {
  violet: "bg-violet-light",
  ember: "bg-ember-light",
};

// A photograph sized and framed like the data cards around it, so the imagery sits in
// the same grid as the numbers rather than being parked in a strip underneath them.
// The caption is always on screen (not hover-only) because these pictures are the point,
// not decoration: the reader should be able to see what they are looking at without
// hunting for it. Colour is held back a little at rest so a photo never out-shouts the
// chart beside it, and comes back fully on hover.
export default function PhotoPanel({
  photo,
  accent = "violet",
  tag,
  className = "",
  style,
  focus = "center",
}: PhotoPanelProps) {
  return (
    <figure
      className={`anim-fade-in-up group relative overflow-hidden rounded-2xl border shadow-xl shadow-black/40 transition-colors duration-300 ${ringClass[accent]} ${className}`}
      style={style}
    >
      <img
        src={photo.src}
        alt={photo.alt}
        loading="lazy"
        className="h-full w-full object-cover opacity-90 saturate-[0.9] transition-all duration-500 ease-out group-hover:scale-[1.04] group-hover:opacity-100 group-hover:saturate-100"
        style={{ objectPosition: focus }}
      />
      <div className="grain-overlay" />

      <div
        className={`pointer-events-none absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t ${glowClass[accent]} via-ink/40 to-transparent opacity-40 mix-blend-multiply`}
      />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/3 bg-gradient-to-t from-ink via-ink/65 to-transparent" />

      {tag && (
        <span className="pointer-events-none absolute left-4 top-4 rounded-full border border-white/20 bg-ink/60 px-2.5 py-1 font-mono text-[10px] uppercase tracking-widest text-white/70 backdrop-blur-sm">
          {tag}
        </span>
      )}

      <figcaption className="pointer-events-none absolute inset-x-0 bottom-0 flex items-center gap-2 px-4 pb-4">
        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${dotClass[accent]}`} />
        <span className="font-mono text-[11px] uppercase leading-tight tracking-wide text-white/80">
          {photo.caption}
        </span>
      </figcaption>
    </figure>
  );
}
