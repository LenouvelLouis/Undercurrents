// Three bars bouncing out of phase: the "now playing" mark next to the active page.
// Pure CSS so it costs nothing, and frozen by the reduced-motion block in base.css.
export default function Equalizer({ className = "" }: { className?: string }) {
  return (
    <span aria-hidden className={`inline-flex h-3 items-end gap-[2px] ${className}`}>
      <span className="eq-bar" style={{ animationDelay: "-0.2s" }} />
      <span className="eq-bar" style={{ animationDelay: "-0.55s" }} />
      <span className="eq-bar" style={{ animationDelay: "-0.9s" }} />
    </span>
  );
}
