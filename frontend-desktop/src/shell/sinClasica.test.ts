import { describe, expect, test } from "vitest";

// Retiro de Streamlit (F10): la interfaz React es la unica. Ningun archivo de codigo (no de pruebas) vuelve a nombrar
// la direccion de la clasica, el estado «sin migrar» ni los campos de la API que desaparecieron.
const FUENTES = import.meta.glob("../**/*.{ts,tsx,scss}", { query: "?raw", import: "default", eager: true }) as Record<
  string,
  string
>;

const PROHIBIDO: [string, RegExp][] = [
  ["url_clasica", /url_clasica/],
  ["urlClasica", /urlClasica/],
  ["VITE_URL_CLASICA", /VITE_URL_CLASICA/],
  ["enlaceClasico", /enlaceClasico/],
  ["estaMigrada", /estaMigrada/],
  ["PaginaSinMigrar", /PaginaSinMigrar/],
  ["api_activa", /api_activa/],
  ["puerto_api", /puerto_api/],
  ["textoDeApi", /textoDeApi/],
  ["«interfaz clásica»", /interfaz cl[aá]sica/i],
  ["clases del menu «sin migrar»", /silice-menu__(clasica|pendiente|grupo|titulo)/],
];

describe("sin rastro de la interfaz clasica", () => {
  const archivos = Object.entries(FUENTES).filter(([ruta]) => !/\.test\.tsx?$/.test(ruta));

  test("el barrido ve el codigo de la interfaz", () => {
    expect(archivos.length).toBeGreaterThan(100);
  });

  test.each(PROHIBIDO)("ningun archivo de codigo dice %s", (_nombre, patron) => {
    const culpables = archivos.filter(([, texto]) => patron.test(texto)).map(([ruta]) => ruta);
    expect(culpables).toEqual([]);
  });
});
