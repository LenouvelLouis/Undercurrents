import { motion } from "motion/react";

interface UndercurrentProps {
  className?: string;
  lines?: number;
  /** CSS colour for the strokes; defaults to the current text colour. */
  color?: string;
  opacity?: number;
}

// The house motif: a stack of slow sine lines drifting sideways, the "current" under the
// surface. Each path is two periods long and slides by exactly one period, so the loop has
// no seam. MotionConfig reducedMotion="user" in App stops the drift for people who ask.
const PERIOD = 400;

function wave(amplitude: number, y: number, phase: number) {
  const pts: string[] = [];
  for (let x = 0; x <= PERIOD * 3; x += 10) {
    const v = y + Math.sin(((x + phase) / PERIOD) * Math.PI * 2) * amplitude;
    pts.push(`${x === 0 ? "M" : "L"}${x} ${v.toFixed(1)}`);
  }
  return pts.join(" ");
}

export default function Undercurrent({ className = "", lines = 7, color = "currentColor", opacity = 1 }: UndercurrentProps) {
  return (
    <svg
      aria-hidden
      className={`pointer-events-none ${className}`}
      viewBox={`0 0 ${PERIOD * 2} 200`}
      preserveAspectRatio="none"
      style={{ opacity }}
    >
      {Array.from({ length: lines }, (_, i) => (
        <motion.path
          key={i}
          d={wave(10 + i * 2.2, 40 + i * 20, i * 37)}
          fill="none"
          stroke={color}
          strokeWidth={1}
          vectorEffect="non-scaling-stroke"
          style={{ opacity: 0.25 + (i / lines) * 0.6 }}
          initial={{ x: 0, pathLength: 0 }}
          animate={{ x: -PERIOD, pathLength: 1 }}
          transition={{
            x: { duration: 18 + i * 3, repeat: Infinity, ease: "linear" },
            pathLength: { duration: 1.6, delay: i * 0.08, ease: [0.22, 1, 0.36, 1] },
          }}
        />
      ))}
    </svg>
  );
}
