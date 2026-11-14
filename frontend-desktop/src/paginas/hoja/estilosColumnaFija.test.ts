import { describe, expect, test } from "vitest";

// Pasada en navegador de la ola 2 (D1): al desplazar a lo ancho la tabla de Materiales de la pestaña APU, los campos de
// «Cantidad» (el contenedor del campo de Carbon es `position: relative`) se pintaban ENCIMA de la columna fija
// «Descripción», porque la celda fija (`position: sticky`) no tenía `z-index`. jsdom no calcula el diseño: aquí se
// comprueba que la regla esté escrita; el efecto se midió en navegador (bitácora `2026-11-14-ola2-navegador.md`).
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }
).process;
const estilos = nodo
  .getBuiltinModule("node:fs")
  .readFileSync(`${nodo.cwd()}/src/paginas/hoja/hoja.scss`, "utf-8")
  .replace(/\/\*[\s\S]*?\*\//g, "")
  .replace(/\/\/.*$/gm, "");

describe("la columna fija de una tabla desplazable queda encima de lo que pasa por debajo", () => {
  test("la celda fija de la izquierda lleva z-index", () => {
    const m = /th:first-child,\s*td:first-child\s*\{([^}]*position:\s*sticky[^}]*)\}/.exec(estilos);
    expect(m, "falta la regla de la columna fija").not.toBeNull();
    expect(m![1]).toMatch(/z-index:\s*[1-9]/);
  });
});
