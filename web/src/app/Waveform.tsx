import { useEffect, useRef } from "react";

interface WaveformProps {
  className?: string;
  /** Number of stacked traces; each is phase-shifted from the last. */
  traces?: number;
  /** Two CSS colours the traces blend between. */
  from?: string;
  to?: string;
  amplitude?: number;
}

// An oscilloscope trace: a slow sum of sines, so the page breathes like a signal on a scope. Each trace is drawn three times
// with a small offset in magenta and cyan, the chromatic split that makes it look like light
// through a lens rather than a vector line. Frozen to one frame under reduced motion.
export default function Waveform({ className = "", traces = 4, from = "#e2a6ff", to = "#ff9270", amplitude = 0.36 }: WaveformProps) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0;
    let w = 0;
    let h = 0;
    const dpr = Math.min(2, window.devicePixelRatio || 1);

    const resize = () => {
      const box = canvas.getBoundingClientRect();
      w = box.width;
      h = box.height;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const sample = (x: number, t: number, k: number) => {
      const u = x / w;
      return (
        Math.sin(u * 9 + t * 1.3 + k * 0.7) * 0.55 +
        Math.sin(u * 23 - t * 2.1 + k) * 0.25 +
        Math.sin(u * 51 + t * 3.7 + k * 1.9) * 0.12
      ) * (0.55 + 0.45 * Math.sin(u * Math.PI));
    };

    // Drawing costs: only while on screen and the tab is visible, at most ~30 frames a second.
    // The chromatic ghosts and the glow (shadowBlur is the expensive part) are kept for the
    // leading trace only; the trailing traces are plain thin lines.
    let visible = true;
    const io = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
      if (visible && !raf && !still) raf = requestAnimationFrame(draw);
    });
    io.observe(canvas);
    let last = 0;

    function draw(now: number) {
      raf = 0;
      if (!visible || document.hidden) return;
      if (!still) raf = requestAnimationFrame(draw);
      if (now - last < 32) return;
      last = now;
      const t = now / 1000;
      ctx!.clearRect(0, 0, w, h);
      ctx!.globalCompositeOperation = "lighter";
      const grad = ctx!.createLinearGradient(0, 0, w, 0);
      grad.addColorStop(0, from);
      grad.addColorStop(1, to);
      for (let k = 0; k < traces; k++) {
        const amp = h * amplitude * (1 - k * 0.14);
        const passes: [number, string | CanvasGradient, number, number][] =
          k === 0
            ? [
                [-1.6, "rgba(255,40,190,1)", 0.35, 0],
                [1.6, "rgba(40,220,255,1)", 0.3, 0],
                [0, grad, 0.9, 10],
              ]
            : [[0, grad, 0.75 - k * 0.15, 0]];
        for (const [dx, stroke, alpha, blur] of passes) {
          ctx!.beginPath();
          for (let x = 0; x <= w; x += 4) {
            const y = h / 2 + sample(x, t - k * 0.18, k) * amp;
            if (x === 0) ctx!.moveTo(x + dx, y);
            else ctx!.lineTo(x + dx, y);
          }
          ctx!.strokeStyle = stroke;
          ctx!.globalAlpha = alpha;
          ctx!.lineWidth = k === 0 ? 1.6 : 1;
          ctx!.shadowColor = from;
          ctx!.shadowBlur = blur;
          ctx!.stroke();
        }
      }
      ctx!.globalAlpha = 1;
      ctx!.shadowBlur = 0;
    }
    const onVisibility = () => {
      if (!document.hidden && visible && !raf && !still) raf = requestAnimationFrame(draw);
    };
    document.addEventListener("visibilitychange", onVisibility);
    raf = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(raf);
      io.disconnect();
      ro.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [traces, from, to, amplitude]);

  return <canvas ref={ref} aria-hidden className={`pointer-events-none block w-full ${className}`} />;
}
