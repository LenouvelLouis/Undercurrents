import type { Config } from "tailwindcss";
// Tokens live in tokens.mjs, shared with the marver canvas generator. See that file for why.
import { boxShadow, colors, fontFamily, grainImage } from "./tokens.mjs";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors,
      fontFamily,
      boxShadow,
      backgroundImage: { grain: grainImage },
    },
  },
  plugins: [],
} satisfies Config;
