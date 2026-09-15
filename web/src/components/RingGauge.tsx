import type { Accent } from "../lib/theme";

interface RingGaugeProps {
  percentage: number; // 0-100
  size?: number;
  accent?: Accent;
  children?: React.ReactNode;
}

export default function RingGauge({ percentage, size = 140, accent = "magenta", children }: RingGaugeProps) {
  const strokeWidth = 10;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;
  const strokeClass = accent === "magenta" ? "stroke-magenta" : "stroke-teal";

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth={strokeWidth} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          className={strokeClass}
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
