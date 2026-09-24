import type { CSSProperties, ReactNode } from "react";
import type { Accent } from "../lib/theme";

interface CardProps {
  children: ReactNode;
  tinted?: boolean;
  accent?: Accent;
  className?: string;
  style?: CSSProperties;
}

// Frosted glass over the moving field: the panel blurs whatever colour is flowing behind it,
// so every card picks up the room's light. "Tinted" marks the lead panel of a page with a
// gradient rim in the side's accent instead of a filled box.
const rim: Record<Accent, string> = {
  violet: "before:bg-gradient-to-br before:from-violet-light/70 before:via-violet/20 before:to-transparent",
  ember: "before:bg-gradient-to-br before:from-ember-light/70 before:via-ember/20 before:to-transparent",
};

export default function Card({ children, tinted, accent = "violet", className = "", style }: CardProps) {
  return (
    <div
      className={`relative min-w-0 rounded-[26px] bg-ink/45 p-6 shadow-[0_30px_80px_-40px_rgba(0,0,0,0.8)] ring-1 ring-inset ring-white/[0.07] backdrop-blur-2xl sm:p-7 ${
        tinted
          ? `before:pointer-events-none before:absolute before:inset-0 before:rounded-[26px] before:p-px before:[mask:linear-gradient(#000_0_0)_content-box_exclude,linear-gradient(#000_0_0)] ${rim[accent]}`
          : ""
      } ${className}`}
      style={style}
    >
      {children}
    </div>
  );
}
