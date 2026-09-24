import { motion } from "motion/react";
import type { SideKey } from "./routes";

// The page ground. The two big colour fields drift toward the accent of whichever side is
// open, so moving between Side A and Side B changes the room's light, not just a tab colour.
const FIELDS: Record<SideKey | "home", { a: string; b: string }> = {
  home: { a: "rgba(165,49,214,0.22)", b: "rgba(226,73,47,0.14)" },
  predictions: { a: "rgba(165,49,214,0.24)", b: "rgba(165,49,214,0.08)" },
  analysis: { a: "rgba(226,73,47,0.18)", b: "rgba(217,154,63,0.10)" },
};

export default function Backdrop({ side }: { side: SideKey | "home" }) {
  const f = FIELDS[side];
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-bg">
      <motion.div
        className="absolute -left-[20%] -top-[30%] h-[70vw] w-[70vw] rounded-full blur-[140px]"
        animate={{ backgroundColor: f.a, x: side === "analysis" ? "35vw" : "0vw" }}
        transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
      />
      <motion.div
        className="absolute -bottom-[35%] -right-[15%] h-[60vw] w-[60vw] rounded-full blur-[160px]"
        animate={{ backgroundColor: f.b, x: side === "analysis" ? "-30vw" : "0vw" }}
        transition={{ duration: 1.6, ease: [0.22, 1, 0.36, 1] }}
      />
      <div className="grain-overlay" />
    </div>
  );
}
