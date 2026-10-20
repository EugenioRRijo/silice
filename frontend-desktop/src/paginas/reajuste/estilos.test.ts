import { describe, expect, test } from "vitest";

// Como src/comun/ZonaDeSoltar.test.ts: con `css: false` el `?raw` de un .scss llega vacio; se lee con el modulo de Node.
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const fuente = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/paginas/reajuste/reajuste.scss`, "utf-8");

// Ronda 1 del arbitro, punto 4: el titulo del resultado y la zona del aviso reciben el foco tras «Calcular» (VB-13);
// su anillo es el de Carbon (token `--cds-focus`, 2 px), no el del navegador. jsdom no calcula CSS: se lee el fuente.
describe("Reajuste: anillo de foco de Carbon en lo que recibe el foco tras calcular", () => {
  test("una regla :focus con outline de 2 px en var(--cds-focus) para el titulo y la zona del aviso", () => {
    const i = fuente.indexOf(".silice-reajuste__enfocable:focus");
    expect(i).toBeGreaterThanOrEqual(0);
    const regla = fuente.slice(i, fuente.indexOf("}", i));
    expect(regla).toMatch(/outline:\s*2px solid var\(--cds-focus\)/);
  });
});
