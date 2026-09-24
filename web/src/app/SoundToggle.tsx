import { useEffect, useState } from "react";
import { drone } from "./audio";

// Header control for the drone. The icon is four bars that dance only while sound is on.
export default function SoundToggle() {
  const [on, setOn] = useState(drone.on);
  useEffect(() => {
    const off = drone.subscribe(setOn);
    return () => {
      off();
    };
  }, []);
  return (
    <button
      type="button"
      onClick={() => drone.toggle()}
      aria-pressed={on}
      aria-label={on ? "Turn the ambient drone off" : "Turn on an ambient drone that drives the waveforms"}
      title={on ? "Sound on" : "Sound off"}
      className="flex h-10 items-center gap-2 rounded-full bg-ink/40 px-3.5 text-xs text-white/70 ring-1 ring-white/10 backdrop-blur-xl outline-none transition-colors hover:bg-ink/60 hover:text-white focus-visible:ring-2 focus-visible:ring-white/60"
    >
      <span className={`flex h-3.5 items-end gap-[2px] ${on ? "text-violet-light" : "text-white/50"}`}>
        {[0.35, 0.8, 0.55, 1].map((s, i) => (
          <span
            key={i}
            className={`w-[2px] rounded-full bg-current ${on ? "eq-bar" : ""}`}
            style={{ height: `${s * 100}%`, animationDelay: `${-i * 0.23}s` }}
          />
        ))}
      </span>
      <span className="hidden sm:inline">{on ? "Sound on" : "Sound off"}</span>
    </button>
  );
}
