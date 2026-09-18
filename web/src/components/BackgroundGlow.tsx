export default function BackgroundGlow() {
  const dots = Array.from({ length: 40 }, (_, i) => ({
    left: `${(i * 37) % 100}%`,
    top: `${(i * 53) % 100}%`,
    size: 1 + (i % 3),
    opacity: 0.2 + (i % 5) * 0.1,
  }));

  // A field of concentric, warped lines echoing the Currents sleeve, kept faint and
  // pinned to one corner so it reads as texture, not as a competing illustration.
  const rings = Array.from({ length: 14 }, (_, i) => 40 + i * 26);

  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-bg">
      <div className="absolute -left-1/4 -top-1/4 h-[60vw] w-[60vw] rounded-full bg-violet/20 blur-[120px]" />
      <div className="absolute -right-1/4 top-1/3 h-[50vw] w-[50vw] rounded-full bg-ember/10 blur-[140px]" />
      <div className="absolute bottom-0 left-1/3 h-[35vw] w-[35vw] rounded-full bg-amber/10 blur-[130px]" />

      <svg
        className="absolute -bottom-1/4 -right-1/4 h-[70vw] w-[70vw] opacity-[0.07]"
        viewBox="0 0 600 600"
      >
        {rings.map((r) => (
          <path
            key={r}
            d={`M ${300 - r} 300 Q 300 ${300 - r * 0.6} ${300 + r} 300 Q 300 ${300 + r * 0.6} ${300 - r} 300`}
            fill="none"
            stroke="white"
            strokeWidth={1}
          />
        ))}
      </svg>

      {dots.map((dot, i) => (
        <span
          key={i}
          className="absolute rounded-full bg-white"
          style={{
            left: dot.left,
            top: dot.top,
            width: dot.size,
            height: dot.size,
            opacity: dot.opacity,
          }}
        />
      ))}

      <div className="grain-overlay" />
    </div>
  );
}
