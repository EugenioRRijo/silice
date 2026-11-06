import { describe, expect, test } from "vitest";

// Plan F6, T1: ningún enlace de las pantallas escribe una ruta a mano; todos piden la ruta a `rutaCanonica`
// (`marco/espacios.ts`) para que T4 y T5 muevan las pantallas cambiando un solo lugar. El marco (`src/marco`) es el
// único que conoce las rutas. jsdom no recorre todos los botones en todos sus estados: se lee el fuente, sin comentarios.
interface Fs {
  readdirSync(carpeta: string, opciones: { recursive: true }): string[];
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }).process;
const fs = nodo.getBuiltinModule("node:fs");
const raiz = `${nodo.cwd()}/src`;

const RUTA_A_MANO = /\bto=(?:"\/|\{\s*["'`]\/)|\bnavegar\(\s*["'`]\/|\bnavigate\(\s*["'`]\/|\bhref=(?:"#?\/|\{\s*["'`]#?\/)/;

// `rutaDe` (`/<id>`) tampoco: es la dirección corta de una pantalla, no su ruta canónica.
const IMPORTA_RUTA_DE = /import\s*\{[^}]*\brutaDe\b[^}]*\}\s*from\s*["'][^"']*\/rutas["']/;

function sinComentarios(fuente: string): string {
  return fuente
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .split(/\r?\n/)
    .map((linea) => linea.replace(/(^|[^:"'`])\/\/.*$/, "$1"))
    .join("\n");
}

const fuentes = ["paginas", "comun", "shell"].flatMap((carpeta) =>
  fs
    .readdirSync(`${raiz}/${carpeta}`, { recursive: true })
    .map((r) => `${carpeta}/${r.replaceAll("\\", "/")}`)
    .filter((r) => /\.tsx?$/.test(r) && !/\.test\.tsx?$/.test(r)),
);

describe("ningún enlace interno escribe una ruta a mano", () => {
  test("la guardia detecta los enlaces con ruta escrita y deja pasar los que la piden a rutaCanonica", () => {
    expect(RUTA_A_MANO.test('<Link className="x" to="/hoja">')).toBe(true);
    expect(RUTA_A_MANO.test("<Link to={`/obra/${id}`}>")).toBe(true);
    expect(RUTA_A_MANO.test('void navegar("/libros");')).toBe(true);
    expect(RUTA_A_MANO.test('navigate( "/x" )')).toBe(true);
    expect(RUTA_A_MANO.test('<a href="#/pendientes">')).toBe(true);
    expect(RUTA_A_MANO.test('<Link to={rutaCanonica("hoja")}>')).toBe(false);
    expect(RUTA_A_MANO.test('void navegar(rutaCanonica("libros") ?? "/");')).toBe(false);
    expect(RUTA_A_MANO.test('<a href="https://ejemplo.org/x">')).toBe(false);
  });

  test("ninguna pantalla, pieza común ni pieza del armazón la escribe", () => {
    expect(fuentes.length).toBeGreaterThan(100); // la guardia no recorre una lista vacia
    const conRutaAMano = fuentes.filter((r) => RUTA_A_MANO.test(sinComentarios(fs.readFileSync(`${raiz}/${r}`, "utf-8"))));
    expect(conRutaAMano).toEqual([]);
  });

  test("ninguna pieza arma la dirección corta /<id> con rutaDe de shell/rutas", () => {
    expect(IMPORTA_RUTA_DE.test('import { paginaPorId, rutaDe, usable } from "../../shell/rutas";')).toBe(true);
    expect(IMPORTA_RUTA_DE.test('import { rutaDe } from "./rutas";')).toBe(true);
    expect(IMPORTA_RUTA_DE.test('import { paginaPorId, usable } from "../../shell/rutas";')).toBe(false);
    const conRutaDe = fuentes.filter((r) => IMPORTA_RUTA_DE.test(sinComentarios(fs.readFileSync(`${raiz}/${r}`, "utf-8"))));
    expect(conRutaDe).toEqual([]);
  });
});
