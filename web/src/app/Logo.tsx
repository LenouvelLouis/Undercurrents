// Eight dots on a ring around a centre: the old mark, drawn once here for every place that
// needs it.
export default function Logo({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 28 28" className={className} aria-hidden>
      <defs>
        <linearGradient id="uc-logo" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="28" y2="28">
          <stop offset="0%" stopColor="#e2a6ff" />
          <stop offset="100%" stopColor="#ff9270" />
        </linearGradient>
      </defs>
      <circle cx="14" cy="14" r="2.2" fill="url(#uc-logo)" />
      {Array.from({ length: 8 }, (_, i) => {
        const t = (i / 8) * Math.PI * 2;
        return <circle key={i} cx={14 + Math.cos(t) * 10} cy={14 + Math.sin(t) * 10} r="1.6" fill="url(#uc-logo)" opacity={0.9} />;
      })}
    </svg>
  );
}
