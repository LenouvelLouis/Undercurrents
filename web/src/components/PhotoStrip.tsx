import type { CSSProperties } from "react";
import type { Accent } from "../lib/theme";

interface PhotoStripItem {
  src: string;
  alt: string;
}

interface PhotoStripProps {
  images: PhotoStripItem[];
  accent?: Accent;
  className?: string;
}

const ringColor: Record<Accent, string> = {
  violet: "ring-violet/30 hover:ring-violet/60",
  ember: "ring-ember/30 hover:ring-ember/60",
};

const accentHex: Record<Accent, string> = {
  violet: "#a531d6",
  ember: "#e2492f",
};

// Real band/album photography, worked into the page two ways depending on how much
// true margin is available beside the centered content column (now max-w-[112rem], up
// from 80rem then 96rem, so the column itself uses nearly all of a normal 1920px
// screen). Below ~2300px there's no room to spare beside that wider column, so photos
// run as a loose strip under the page's data (unchanged from before). From ~2300px up
// (a true ultrawide/4K window), there's still margin left over for a second, bigger
// treatment:
// two stacked piles of photo blocks pinned to the outer edges, tied to the page with a
// small mono label and a spine line growing out of the content column, so the pile
// reads as attached to the page rather than floating independently in the margin. Both
// are purely decorative: never a click target, never data-bearing.
export default function PhotoStrip({ images, accent = "violet", className = "" }: PhotoStripProps) {
  const left = images.filter((_, i) => i % 2 === 0);
  const right = images.filter((_, i) => i % 2 === 1);

  return (
    <>
      <div className={`mt-10 flex flex-wrap items-end gap-4 min-[2300px]:hidden ${className}`}>
        {images.map((img, i) => (
          <div
            key={img.src + i}
            className={`anim-fade-in-up group relative overflow-hidden rounded-xl shadow-lg shadow-black/40 ring-1 transition-all ${ringColor[accent]}`}
            style={{
              width: 92 + (i % 3) * 22,
              height: 92 + (i % 3) * 22,
              animationDelay: `${0.3 + i * 0.06}s`,
            }}
          >
            <img
              src={img.src}
              alt={img.alt}
              className="h-full w-full object-cover grayscale contrast-125 opacity-70 transition-opacity duration-300 group-hover:opacity-100 group-hover:grayscale-0"
            />
            <div className="grain-overlay" />
            <div className="pointer-events-none absolute inset-x-0 bottom-0 translate-y-2 bg-gradient-to-t from-black/90 via-black/50 to-transparent px-2 pb-1.5 pt-5 opacity-0 transition-all duration-300 group-hover:translate-y-0 group-hover:opacity-100">
              <span className="text-[11px] line-clamp-2 leading-tight text-white/90">{img.alt}</span>
            </div>
          </div>
        ))}
      </div>

      <PhotoRail side="left" images={left} accent={accent} />
      <PhotoRail side="right" images={right} accent={accent} />
    </>
  );
}

// Pinned with `fixed` (not part of page flow) so the pile stays put in the margin as
// the page scrolls. Position is computed from the page's own 112rem content column
// (max-w-[112rem]) rather than the raw viewport edge, so it always lands just outside
// the content regardless of how much wider the screen is: 56rem half-width + 1.5rem gap
// + 13rem rail width = 70.5rem from center. Anchored near the top of the viewport
// (rather than vertical-center) with a short label and a spine line reaching back
// toward the content edge, so the pile visibly grows out of the page instead of
// hovering unattached in the margin.
function PhotoRail({ side, images, accent }: { side: "left" | "right"; images: PhotoStripItem[]; accent: Accent }) {
  if (images.length === 0) return null;
  const offset: CSSProperties = side === "left" ? { left: "calc(50% - 70.5rem)" } : { right: "calc(50% - 70.5rem)" };
  const spineSide: CSSProperties = side === "left" ? { right: -20 } : { left: -20 };
  return (
    <div className="fixed top-36 z-0 hidden max-h-[68vh] w-52 flex-col min-[2300px]:flex" style={offset}>
      <div className={`text-[13px] font-medium mb-3 flex items-center gap-2 text-white/45 ${side ==="right" ? "flex-row-reverse text-right" : ""}`}>
        <span className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ backgroundColor: accentHex[accent] }} />
        from the archive
      </div>
      <div className="relative flex-1 overflow-hidden">
        <span
          className="pointer-events-none absolute top-0 h-full w-px opacity-40"
          style={{ ...spineSide, background: `linear-gradient(to bottom, ${accentHex[accent]}, transparent 70%)` }}
        />
        {images.map((img, i) => (
          <div
            key={img.src + i}
            className={`anim-fade-in-up group relative aspect-square w-full shrink-0 overflow-hidden rounded-2xl border border-white/10 shadow-2xl shadow-black/50 ring-1 transition-all ${ringColor[accent]}`}
            style={{
              transform: `rotate(${i % 2 === 0 ? -3 : 3}deg)`,
              marginTop: i === 0 ? 0 : -16,
              animationDelay: `${0.25 + i * 0.1}s`,
            }}
          >
            <img
              src={img.src}
              alt={img.alt}
              className="h-full w-full object-cover grayscale contrast-125 opacity-75 transition-all duration-300 group-hover:rotate-0 group-hover:opacity-100 group-hover:grayscale-0"
            />
            <div className="grain-overlay" />
            <div className="pointer-events-none absolute inset-x-0 bottom-0 translate-y-2 bg-gradient-to-t from-black/90 via-black/50 to-transparent px-2.5 pb-2 pt-6 opacity-0 transition-all duration-300 group-hover:translate-y-0 group-hover:opacity-100 group-hover:rotate-0">
              <span className="text-[11px] line-clamp-2 leading-tight text-white/90">{img.alt}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
