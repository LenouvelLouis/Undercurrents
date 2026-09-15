export default function BackgroundGlow() {
  const dots = Array.from({ length: 40 }, (_, i) => ({
    left: `${(i * 37) % 100}%`,
    top: `${(i * 53) % 100}%`,
    size: 1 + (i % 3),
    opacity: 0.2 + (i % 5) * 0.1,
  }));

  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-bg">
      <div className="absolute -left-1/4 -top-1/4 h-[60vw] w-[60vw] rounded-full bg-magenta/20 blur-[120px]" />
      <div className="absolute -right-1/4 top-1/3 h-[50vw] w-[50vw] rounded-full bg-teal/10 blur-[140px]" />
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
    </div>
  );
}
