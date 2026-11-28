import * as sass from "sass";
import { describe, expect, test } from "vitest";

// Cada hoja .scss del front compila con Sass (2026-11-27). Vitest no compila los estilos que importa cada componente: un
// error de sintaxis (una llave de más en marco/BarraSuperior.scss, desde C3-C5) solo lo veía `npm run build`.
interface Fs {
  readdirSync(ruta: string, opciones: { recursive: true }): string[];
}
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }).process;
const RAIZ = `${nodo.cwd()}/src`;
const HOJAS = nodo
  .getBuiltinModule("node:fs")
  .readdirSync(RAIZ, { recursive: true })
  .map((ruta) => ruta.replaceAll("\\", "/"))
  .filter((ruta) => ruta.endsWith(".scss") && !ruta.split("/").pop()!.startsWith("_"));

describe("todas las hojas de estilo compilan", () => {
  test("hay hojas que revisar", () => {
    expect(HOJAS.length).toBeGreaterThan(20);
  });

  test.each(HOJAS)("%s compila", (ruta) => {
    expect(() => sass.compile(`${RAIZ}/${ruta}`, { loadPaths: [`${nodo.cwd()}/node_modules`], quietDeps: true, silenceDeprecations: ["import"] })).not.toThrow();
  });
});
