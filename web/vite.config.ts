import react from "@vitejs/plugin-react";
import autoprefixer from "autoprefixer";
import tailwindcss from "tailwindcss";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  // PostCSS is declared here rather than in a standalone postcss.config.js on purpose. The
  // marver design canvas runs its own Vite server from this same directory, and Vite
  // auto-discovers a root postcss.config.js: the app's Tailwind 3 plugin was therefore also
  // processing design/theme.css, which marver compiles with Tailwind 4, and the two collided
  // ("`@layer base` is used but no matching `@tailwind base` directive is present").
  // Declaring the plugins inline keeps Tailwind 3 scoped to the app's own build.
  css: {
    postcss: {
      plugins: [tailwindcss(), autoprefixer()],
    },
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
