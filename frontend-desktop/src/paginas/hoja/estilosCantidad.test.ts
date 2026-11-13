import { describe, expect, test } from "vitest";

// E2E-3i (prueba de punta a punta del 2026-11-13): en la pestaña APU, a 1366 px, una cantidad de 0,001 se leía «0,00». El
// servidor manda «0,001» entero (`texto_de_cifra`); lo cortaba el campo: la columna estrecha deja al campo de Carbon `sm`
// 31 px de texto y «0,001» mide 40 (simulación en navegador, bitácora `2026-11-13-ola2-front.md` §1). La regla elegida: el
// campo de la cantidad (y el del desperdicio) mide lo que mide lo escrito, con un mínimo. jsdom no calcula el diseño:
// aquí se comprueba que la regla esté escrita; el efecto se midió en navegador.
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

describe("la cantidad de una línea del APU se lee entera", () => {
  test("el campo de la tabla del APU crece con lo escrito y no baja de un mínimo", () => {
    const m = /\.silice-hoja__apu-centro td \.cds--text-input\s*\{([^}]*)\}/.exec(estilos);
    expect(m, "falta la regla del campo de la cantidad en la tabla del APU").not.toBeNull();
    expect(m![1]).toMatch(/field-sizing:\s*content/);
    expect(m![1]).toMatch(/min-inline-size:\s*calc\(4ch \+ 2rem\)/);
  });
});
