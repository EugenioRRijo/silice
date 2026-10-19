import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Interfaz nueva de Silice, servida por el FastAPI en /app (RS2-9).
export default defineConfig({
  base: "/app/",
  plugins: [react()],
  server: {
    proxy: {
      "/v1": "http://127.0.0.1:8000",
    },
  },
  build: {
    sourcemap: false,
  },
  css: {
    preprocessorOptions: {
      scss: {
        // Los avisos de @carbon/styles con la API de Sass vigente no son nuestros.
        quietDeps: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: false,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}", "scripts/**/*.test.mjs"],
    css: false,
  },
});
