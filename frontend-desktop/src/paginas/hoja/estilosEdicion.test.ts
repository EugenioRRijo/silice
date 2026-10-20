import { describe, expect, test } from "vitest";

// Con `css: false` el `?raw` de un .scss llega vacío (como en reajuste/estilos.test.ts): se lee con el módulo de Node.
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const estilos = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/paginas/hoja/hoja.scss`, "utf-8");

// La edición de las tablas anchas (3c-1): la columna fija no puede tapar el campo enfocado (WCAG 2.4.11). jsdom no
// calcula el diseño, así que se comprueba que la regla esté escrita; la medición real es de la auditoría visual (T11).
describe("estilos de las tablas editables del espacio", () => {
  test("el desplazamiento por foco deja el margen de la columna fija", () => {
    const bloque = /\.silice-hoja__editable\s*\{([\s\S]*?)\n\}/.exec(estilos);
    expect(bloque).not.toBeNull();
    expect(bloque![1]).toMatch(/scroll-padding-inline-start:\s*9rem/);
    expect(bloque![1]).toMatch(/max-inline-size:\s*8rem/); // la columna fija mide 8 rem: menos que el margen
  });

  test("la región desplazable no deja salir la tabla de la página", () => {
    expect(estilos).toMatch(/\.silice-hoja__desplazable\s*\{[^}]*overflow-x:\s*auto/);
  });
});
