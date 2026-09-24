import { useEffect, useRef } from "react";

export type FieldMood = "home" | "predictions" | "analysis" | "menu";

// The house background: domain-warped noise pushed through the sleeve palette, with contour
// bands that echo the Currents cover. One full-screen WebGL quad, drawn at a third of the
// screen's resolution (it is all blur anyway) and paused when the tab is hidden. Moving
// between sides eases the palette rather than swapping it. With reduced motion it renders one
// still frame; without WebGL it falls back to a CSS gradient.
const FRAG = `
precision mediump float;
uniform vec2 r; uniform float t; uniform float side; uniform float glow;
float h(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float n(vec2 p){vec2 i=floor(p),f=fract(p);vec2 u=f*f*(3.-2.*f);
  return mix(mix(h(i),h(i+vec2(1.,0.)),u.x),mix(h(i+vec2(0.,1.)),h(i+vec2(1.,1.)),u.x),u.y);}
float fbm(vec2 p){float v=0.,a=.5;for(int i=0;i<5;i++){v+=a*n(p);p=p*2.03+vec2(1.7,9.2);a*=.5;}return v;}
void main(){
  vec2 uv=gl_FragCoord.xy/r; vec2 p=uv*vec2(r.x/r.y,1.)*1.5;
  float tt=t*.035;
  vec2 q=vec2(fbm(p+tt),fbm(p+vec2(5.2,1.3)-tt));
  vec2 w=vec2(fbm(p+3.*q+vec2(1.7,9.2)+tt*1.4),fbm(p+3.*q+vec2(8.3,2.8)-tt));
  float f=fbm(p+3.4*w);
  vec3 ink=vec3(.035,.016,.047);
  vec3 violet=vec3(.62,.18,.82), orchid=vec3(.86,.55,.98);
  vec3 ember=vec3(.88,.28,.17), amber=vec3(.9,.62,.28);
  vec3 a=mix(violet,ember,side), b=mix(ember,amber,side), c=mix(orchid,amber,side);
  vec3 col=mix(ink,a,smoothstep(.38,.98,f));
  col=mix(col,b,smoothstep(.55,1.05,length(w))*.5);
  float bands=smoothstep(.82,1.,.5+.5*sin(f*26.-t*.25));
  col+=bands*.12*smoothstep(.45,.9,f)*c;
  col=mix(ink,col,glow);
  float v=smoothstep(1.25,.15,length((uv-.5)*vec2(1.2,1.)));
  col*=mix(.45,1.,v);
  gl_FragColor=vec4(col,1.);
}`;

const TARGET: Record<FieldMood, { side: number; glow: number }> = {
  home: { side: 0.35, glow: 1 },
  menu: { side: 0.5, glow: 1 },
  predictions: { side: 0, glow: 0.42 },
  analysis: { side: 1, glow: 0.42 },
};

export default function LiquidField({ mood }: { mood: FieldMood }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const moodRef = useRef(mood);
  moodRef.current = mood;

  useEffect(() => {
    const canvas = canvasRef.current;
    const gl = canvas?.getContext("webgl", { antialias: false, premultipliedAlpha: false });
    if (!canvas || !gl) {
      canvas?.classList.add("liquid-fallback");
      return;
    }
    const compile = (type: number, src: string) => {
      const s = gl.createShader(type)!;
      gl.shaderSource(s, src);
      gl.compileShader(s);
      return s;
    };
    const prog = gl.createProgram()!;
    gl.attachShader(prog, compile(gl.VERTEX_SHADER, "attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}"));
    gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, FRAG));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      canvas.classList.add("liquid-fallback");
      return;
    }
    gl.useProgram(prog);
    const buf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
    const loc = gl.getAttribLocation(prog, "p");
    gl.enableVertexAttribArray(loc);
    gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
    const uR = gl.getUniformLocation(prog, "r");
    const uT = gl.getUniformLocation(prog, "t");
    const uSide = gl.getUniformLocation(prog, "side");
    const uGlow = gl.getUniformLocation(prog, "glow");

    const SCALE = 0.34;
    const resize = () => {
      canvas.width = Math.max(1, Math.round(window.innerWidth * SCALE));
      canvas.height = Math.max(1, Math.round(window.innerHeight * SCALE));
      gl.viewport(0, 0, canvas.width, canvas.height);
    };
    resize();
    window.addEventListener("resize", resize);

    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const start = performance.now() - 40_000; // start mid-flow, not from a flat first frame
    let side = TARGET[moodRef.current].side;
    let glow = TARGET[moodRef.current].glow;
    let raf = 0;
    let last = 0;

    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (document.hidden || now - last < 33) return; // ~30 fps is plenty for a slow field
      last = now;
      const target = TARGET[moodRef.current];
      side += (target.side - side) * 0.04;
      glow += (target.glow - glow) * 0.05;
      gl.uniform2f(uR, canvas.width, canvas.height);
      gl.uniform1f(uT, (now - start) / 1000);
      gl.uniform1f(uSide, side);
      gl.uniform1f(uGlow, glow);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };

    if (still) {
      const drawStill = () => {
        const target = TARGET[moodRef.current];
        gl.uniform2f(uR, canvas.width, canvas.height);
        gl.uniform1f(uT, 40);
        gl.uniform1f(uSide, target.side);
        gl.uniform1f(uGlow, target.glow);
        gl.drawArrays(gl.TRIANGLES, 0, 3);
      };
      drawStill();
      const id = window.setInterval(drawStill, 500);
      return () => {
        window.clearInterval(id);
        window.removeEventListener("resize", resize);
      };
    }
    raf = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 bg-bg">
      <canvas ref={canvasRef} className="hue-drift h-full w-full" />
      <div className="grain-overlay" />
    </div>
  );
}
