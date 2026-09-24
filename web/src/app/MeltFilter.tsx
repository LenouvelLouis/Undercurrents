// One SVG filter shared by every photo: fractal noise whose frequency breathes, used to push
// the image's pixels sideways so a hovered photograph ripples like a heat haze over a stage.
export default function MeltFilter() {
  return (
    <svg aria-hidden width="0" height="0" className="absolute">
      <filter id="uc-melt" x="-10%" y="-10%" width="120%" height="120%">
        <feTurbulence type="fractalNoise" baseFrequency="0.008 0.02" numOctaves="2" seed="7" result="noise">
          <animate attributeName="baseFrequency" dur="7s" values="0.008 0.02;0.014 0.035;0.008 0.02" repeatCount="indefinite" />
        </feTurbulence>
        <feDisplacementMap in="SourceGraphic" in2="noise" scale="28" xChannelSelector="R" yChannelSelector="G" />
      </filter>
    </svg>
  );
}
