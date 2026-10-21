import { describe, expect, test } from "vitest";

// Retiro de Streamlit (F10): la interfaz React es la unica. Ningun archivo de codigo (no de pruebas) vuelve a nombrar
// la direccion de la clasica, el estado «sin migrar» ni los campos de la API que desaparecieron.
const FUENTES = import.meta.glob("../**/*.{ts,tsx}", { query: "?raw", import: "default", eager: true }) as Record<
  string,
  string
>;

// Con `css: false` el `?raw` de un .scss llega vacio (el barrido pasaria en vacio): los estilos se leen con el modulo de Node.
type ModuloFs = { readdirSync(ruta: string, opciones: { recursive: true }): string[]; readFileSync(ruta: string, codificacion: string): string };
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: string): ModuloFs } }).process;
const fs = nodo.getBuiltinModule("node:fs");
const ESTILOS: Record<string, string> = Object.fromEntries(
  fs
    .readdirSync(`${nodo.cwd()}/src`, { recursive: true })
    .map((ruta) => ruta.replaceAll("\\", "/"))
    .filter((ruta) => ruta.endsWith(".scss"))
    .map((ruta) => [`../${ruta}`, fs.readFileSync(`${nodo.cwd()}/src/${ruta}`, "utf-8")]),
);

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
  const archivos = Object.entries({ ...FUENTES, ...ESTILOS }).filter(([ruta]) => !/\.test\.tsx?$/.test(ruta));

  test("el barrido ve el codigo de la interfaz", () => {
    expect(archivos.length).toBeGreaterThan(100);
  });

  test("el barrido lee los estilos con su contenido", () => {
    const scss = archivos.filter(([ruta]) => ruta.endsWith(".scss"));
    expect(scss.length).toBeGreaterThan(0);
    expect(scss.every(([, texto]) => texto.length > 0)).toBe(true);
  });

  test.each(PROHIBIDO)("ningun archivo de codigo dice %s", (_nombre, patron) => {
    const culpables = archivos.filter(([, texto]) => patron.test(texto)).map(([ruta]) => ruta);
    expect(culpables).toEqual([]);
  });
});
