import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// Interfaz nueva de Silice, servida por el FastAPI en /app (RS2-9).
export default defineConfig({
  base: "/app/",
  plugins: [react()],
  server: {
    // Solo desde este equipo: con `--host` el proxy anularia la regla de «solo desde el propio equipo» (RM-4).
    host: "127.0.0.1",
    strictPort: true,
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
    rollupOptions: {
      output: {
        // react-router en un trozo con nombre fijo: scripts/verificar_dist.mjs permite sus textos de error y de aviso
        // (reactrouter.com, localhost, github.com) solo en el bundle principal o en este trozo (RNF-22, RS2B-2).
        manualChunks(id: string) {
          return /[\\/]node_modules[\\/]react-router/.test(id) ? "enrutador" : undefined;
        },
      },
    },
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
