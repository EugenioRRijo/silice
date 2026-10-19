import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Interfaz nueva de Silice, servida por el FastAPI en /app (RS2-9).
export default defineConfig({
  base: "/app/",
  plugins: [react()],
  server: {
    proxy: {
      "/v1": "http://127.0.0.1:8000",
      // Rutas de la API sin prefijo que usan las paginas migradas (ola 2): presupuestos, listas, computos, partidas.
      "/presupuestos": "http://127.0.0.1:8000",
      "/listas-precios": "http://127.0.0.1:8000",
      "/computos": "http://127.0.0.1:8000",
      "/partidas": "http://127.0.0.1:8000",
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
    // Las pruebas que escriben contrasenas largas con userEvent se acercan a los 5 s de Vitest cuando corren
    // todos los archivos a la vez (CI y laptops lentas): 20 s evita falsos rojos sin esconder cuelgues reales.
    testTimeout: 20_000,
  },
});
