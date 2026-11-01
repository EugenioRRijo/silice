import { describe, expect, test } from "vitest";

// jsdom no calcula CSS: las reglas se leen del fuente (como marco/estilosMarco.test.ts) y se midieron en el navegador.
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const leer = (ruta: string) => nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/${ruta}`, "utf-8");

function reglaDe(fuente: string, selector: string): string {
  const i = fuente.indexOf(`${selector} {`);
  if (i < 0) return "";
  const abre = fuente.indexOf("{", i);
  return fuente.slice(i, fuente.indexOf("}", abre));
}

// Pasada de navegador a 1366x768 (31-10): en Control › Valuaciones la columna «Total con IVA» quedaba cortada a la derecha.
describe("las tablas de Control caben en su contenedor", () => {
  const scss = leer("paginas/control/control.scss");

  test("celdas con relleno compacto para que las nueve columnas de las valuaciones quepan", () => {
    expect(reglaDe(scss, ".silice-control__bloque .silice-tabla :is(th, td)")).toMatch(/padding-inline:\s*0\.5rem/);
  });

  test("las cifras no se parten y su encabezado se lee entero", () => {
    expect(reglaDe(scss, ".silice-control__bloque .silice-tabla .silice-cifra")).toMatch(/white-space:\s*nowrap/);
  });
});
