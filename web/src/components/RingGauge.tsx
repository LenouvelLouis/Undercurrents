import type { Accent } from "../lib/theme";

interface RingGaugeProps {
  percentage: number; // 0-100
  size?: number;
  accent?: Accent;
  children?: React.ReactNode;
}

export default function RingGauge({ percentage, size = 140, accent = "violet", children }: RingGaugeProps) {
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;
  const gradientId = `ring-grad-${accent}`;
  const gradientStops =
    accent === "violet" ? ["#e2a6ff", "#a531d6"] : ["#ff9270", "#e2492f"];

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id={gradientId} gradientUnits="userSpaceOnUse" x1="0" y1="0" x2={size} y2={size}>
            <stop offset="0%" stopColor={gradientStops[0]} />
            <stop offset="100%" stopColor={gradientStops[1]} />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth={strokeWidth} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        {children ?? <span className="font-display text-2xl font-bold">{Math.round(percentage)}%</span>}
      </div>
    </div>
  );
}
