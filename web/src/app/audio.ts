// An optional ambient drone, generated in the browser: three detuned saw oscillators through a
// low-pass filter swept by a slow LFO, into a feedback delay. No recording is played; every
// sound is synthesised here. It exists so the waveforms on the page have a real signal to draw
// when the listener opts in. Off by default, and nothing is created until the first click.
type Listener = (on: boolean) => void;

class Drone {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  analyser: AnalyserNode | null = null;
  on = false;
  private listeners = new Set<Listener>();

  subscribe(fn: Listener) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  private build() {
    const ctx = new AudioContext();
    const master = ctx.createGain();
    master.gain.value = 0;
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 2048;
    analyser.smoothingTimeConstant = 0.85;

    const filter = ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 700;
    filter.Q.value = 9;
    const lfo = ctx.createOscillator();
    lfo.frequency.value = 0.07;
    const lfoDepth = ctx.createGain();
    lfoDepth.gain.value = 520;
    lfo.connect(lfoDepth).connect(filter.frequency);
    lfo.start();

    // A minor-ish cluster around A1/E2/A2, slightly detuned so it phases like a flanger
    for (const [freq, detune] of [[55, -7], [82.4, 6], [110, 3], [164.8, -4]] as const) {
      const osc = ctx.createOscillator();
      osc.type = "sawtooth";
      osc.frequency.value = freq;
      osc.detune.value = detune;
      const g = ctx.createGain();
      g.gain.value = 0.09;
      osc.connect(g).connect(filter);
      osc.start();
    }

    const delay = ctx.createDelay(2);
    delay.delayTime.value = 0.42;
    const feedback = ctx.createGain();
    feedback.gain.value = 0.45;
    filter.connect(delay);
    delay.connect(feedback).connect(delay);

    filter.connect(master);
    delay.connect(master);
    master.connect(analyser);
    analyser.connect(ctx.destination);

    this.ctx = ctx;
    this.master = master;
    this.analyser = analyser;
  }

  async toggle() {
    if (!this.ctx) this.build();
    const ctx = this.ctx!;
    if (ctx.state === "suspended") await ctx.resume();
    this.on = !this.on;
    const now = ctx.currentTime;
    this.master!.gain.cancelScheduledValues(now);
    this.master!.gain.setTargetAtTime(this.on ? 0.22 : 0, now, this.on ? 1.2 : 0.4);
    this.listeners.forEach((fn) => fn(this.on));
  }
}

export const drone = new Drone();
