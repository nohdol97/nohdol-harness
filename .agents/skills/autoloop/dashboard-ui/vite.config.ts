import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: false,
    cssCodeSplit: false,
    rollupOptions: { output: { entryFileNames: "assets/app.js", assetFileNames: "assets/app.[ext]", manualChunks: undefined } }
  },
  test: { environment: "jsdom", setupFiles: ["./tests/setup.ts"] }
});
