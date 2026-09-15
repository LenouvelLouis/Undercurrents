import type { ReactNode } from "react";
import type { Accent } from "../lib/theme";
import { accentCardTint } from "../lib/theme";

interface CardProps {
  children: ReactNode;
  tinted?: boolean;
  accent?: Accent;
  className?: string;
}

export default function Card({ children, tinted, accent = "magenta", className = "" }: CardProps) {
  const tint = tinted ? accentCardTint[accent] : "bg-white/[0.02] border-white/10";
  return <div className={`rounded-xl border p-6 ${tint} ${className}`}>{children}</div>;
}
