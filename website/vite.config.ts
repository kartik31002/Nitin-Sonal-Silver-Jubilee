import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Relative base so the bundle can be hosted under any subpath (e.g. GitHub Pages).
export default defineConfig({
  base: "./",
  plugins: [react()],
  build: {
    target: "es2020",
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
        },
      },
    },
  },
  server: {
    port: 5173,
    open: true,
  },
});
