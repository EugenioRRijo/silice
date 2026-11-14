import { describe, expect, test } from "vitest";

// Resto de la pasada en navegador de F8: la «Carpeta de datos» es una ruta sin espacios que no se partía y empujaba la
// página (1056 px normal; 1056 y 1366 px con letra muy grande). jsdom no calcula el diseño: aquí se comprueba la regla
// escrita; el efecto se MIDE en navegador.
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }
).process;
const leer = (ruta: string): string =>
  nodo
    .getBuiltinModule("node:fs")
    .readFileSync(`${nodo.cwd()}/src/paginas/acerca/${ruta}`, "utf-8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/\/\/.*$/gm, "");

describe("ruta larga de la carpeta de datos", () => {
  test("la celda del valor se parte donde haga falta (overflow-wrap: anywhere)", () => {
    const m = /\.silice-acerca__valor\s*\{([^}]*)\}/.exec(leer("acerca.scss"));
    expect(m, "falta la regla .silice-acerca__valor").not.toBeNull();
    expect(m![1]).toMatch(/overflow-wrap:\s*anywhere/);
  });

  test("la página carga su hoja de estilos y la celda del valor lleva la clase", () => {
    const fuente = leer("index.tsx");
    expect(fuente).toMatch(/import "\.\/acerca\.scss"/);
    expect(fuente).toMatch(/className="silice-acerca__valor"/);
  });
});
