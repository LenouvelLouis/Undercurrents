import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0d0710",
        ink: "#08040c",
        bgglow: "#1a0a20",
        // Predictions accent — pulled from the Currents sleeve's violet/orchid glow.
        violet: {
          DEFAULT: "#a531d6",
          light: "#e2a6ff",
          dark: "#3c0a4a",
        },
        // Data Analysis accent — pulled from The Slow Rush's red room / the Currents
        // vortex trail. Warm, but red rather than orange so it never reads as the
        // Anthropic/Claude brand color.
        ember: {
          DEFAULT: "#e2492f",
          light: "#ff9270",
          dark: "#551408",
        },
        // Rare third accent, kept golden (Innerspeaker's autumn light) so it stays
        // visually distinct from ember — used sparingly, never as a tab identity.
        amber: {
          DEFAULT: "#d99a3f",
          light: "#f0c581",
          dark: "#5f430f",
        },
        cream: "#f3dcb8",
      },
      fontFamily: {
        // Big poster-style wordmark (landing hero, nav logotype) — the "retro-futuristic
        // record sleeve" voice of the site.
        hero: ['"Unbounded"', "sans-serif"],
        // Section titles, numerals, card headings.
        display: ['"Space Grotesk"', "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
        body: ['"Inter"', "sans-serif"],
      },
      boxShadow: {
        "glow-violet": "0 0 60px -12px rgba(165,49,214,0.55)",
        "glow-ember": "0 0 60px -12px rgba(226,73,47,0.5)",
        "glow-amber": "0 0 50px -14px rgba(217,154,63,0.5)",
      },
      backgroundImage: {
        grain:
          "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E\")",
      },
    },
  },
  plugins: [],
} satisfies Config;
