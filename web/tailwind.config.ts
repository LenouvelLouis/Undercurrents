import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0a0a10",
        bgglow: "#12081a",
        magenta: {
          DEFAULT: "#c026d3",
          light: "#e879f9",
          dark: "#701a75",
        },
        teal: {
          DEFAULT: "#2dd4bf",
          light: "#5eead4",
          dark: "#134e4a",
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
        body: ['"Inter"', "sans-serif"],
      },
    },
  },
  plugins: [],
} satisfies Config;
