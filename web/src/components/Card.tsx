import type { CSSProperties, ReactNode } from "react";
import type { Accent } from "../lib/theme";
import { accentCardTint } from "../lib/theme";

interface CardProps {
  children: ReactNode;
  tinted?: boolean;
  accent?: Accent;
  className?: string;
  style?: CSSProperties;
}

export default function Card({ children, tinted, accent = "violet", className = "", style }: CardProps) {
  const tint = tinted ? accentCardTint[accent] : "bg-white/[0.02] border-white/10";
  return (
    <div className={`relative overflow-hidden rounded-2xl border p-6 backdrop-blur-sm ${tint} ${className}`} style={style}>
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />
      {children}
    </div>
  );
}
