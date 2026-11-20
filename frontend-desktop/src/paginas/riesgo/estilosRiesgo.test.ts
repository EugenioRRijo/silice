import { describe, expect, test } from "vitest";

// Con `css: false` el `?raw` de un .scss llega vacío: se lee con el módulo de Node (como estilosBienvenida.test.ts).
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }).process;
const estilos = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/paginas/riesgo/riesgo.scss`, "utf-8");

// jsdom no calcula el diseño: aquí solo se comprueba que la regla esté escrita.
describe("estilos de Riesgo de la obra", () => {
  test("las notas bajo «Serie que mueve cada insumo» ocupan toda la fila de la grilla, no una celda de 14rem", () => {
    expect(estilos).toMatch(/\.riesgo-series \.riesgo-nota[^{]*\{[^}]*grid-column:\s*1 \/ -1/);
  });
});
