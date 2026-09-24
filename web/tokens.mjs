// The single source of truth for Undercurrents' design tokens.
//
// It is a plain .mjs module rather than part of tailwind.config.ts because two build systems
// need it: the app compiles with Tailwind 3 through tailwind.config.ts, and the marver design
// canvas compiles with the Tailwind 4 engine bundled inside marver. A v4 engine cannot read a
// v3 JS config, so design/theme.css is GENERATED from this file by scripts/gen-marver-theme.mjs.
// Change a value here and both worlds move together; edit either consumer by hand and they drift.

export const colors = {
  bg: "#0d0710",
  ink: "#08040c",
  bgglow: "#1a0a20",
  // Predictions accent, pulled from the Currents sleeve's violet/orchid glow.
  violet: { DEFAULT: "#a531d6", light: "#e2a6ff", dark: "#3c0a4a" },
  // Data Analysis accent, pulled from The Slow Rush's red room and the Currents vortex trail.
  // Warm, but red rather than orange so it never reads as the Anthropic/Claude brand colour.
  ember: { DEFAULT: "#e2492f", light: "#ff9270", dark: "#551408" },
  // Rare third accent, kept golden (Innerspeaker's autumn light) so it stays visually distinct
  // from ember. Used sparingly, never as a section identity.
  amber: { DEFAULT: "#d99a3f", light: "#f0c581", dark: "#5f430f" },
  cream: "#f3dcb8",
}

export const fontFamily = {
  // Big poster-style wordmark (landing hero, nav logotype).
  hero: ['"Unbounded"', "sans-serif"],
  // Section titles, numerals, card headings.
  display: ['"Space Grotesk"', "sans-serif"],
  mono: ['"JetBrains Mono"', "monospace"],
  body: ['"Inter"', "sans-serif"],
  // Editorial accent: italic serif for pull quotes, the marquee and single words inside big titles.
  serif: ['"Instrument Serif"', "serif"],
}

export const boxShadow = {
  "glow-violet": "0 0 60px -12px rgba(165,49,214,0.55)",
  "glow-ember": "0 0 60px -12px rgba(226,73,47,0.5)",
  "glow-amber": "0 0 50px -14px rgba(217,154,63,0.5)",
}

export const grainImage =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E\")"

// Chart surfaces. marver's Chart reads its accent, ground and gridline from CSS custom
// properties and falls back to its own blue, which belongs to no brand: the frames feed it
// these instead, and the accent each frame passes is the one its section owns.
export const chart = {
  grid: "rgba(255,255,255,0.08)",
}

// The webfont request the app makes from index.html. The design canvas renders frames in its
// own HTML shell and never sees that file, so the generated stylesheet imports the same faces
// and the frames stop falling back to a system sans.
export const fontImportUrl =
  "https://fonts.googleapis.com/css2?family=Unbounded:wght@600;700;800&family=Space+Grotesk:wght@500;700&family=JetBrains+Mono:wght@400;500&family=Inter:wght@400;500&family=Instrument+Serif:ital@0;1&display=swap"
