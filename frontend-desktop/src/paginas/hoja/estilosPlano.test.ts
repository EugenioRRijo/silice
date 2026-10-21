import { describe, expect, test } from "vitest";

// Con `css: false` el `?raw` de un .scss llega vacío: se lee con el módulo de Node (como estilosEdicion.test.ts).
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const plano = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/paginas/hoja/plano.scss`, "utf-8");
const comun = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/comun/comun.scss`, "utf-8");

// jsdom no calcula el diseño: aquí solo se comprueba que las reglas estén escritas; el efecto se MIDE en navegador (3e-F5).
describe("estilos del flujo Importar plano (3e-2)", () => {
  test("las regiones desplazables contienen a sus descendientes absolutos (las etiquetas ocultas de Carbon)", () => {
    // Sin esto, la etiqueta `cds--visually-hidden` (position: absolute) de cada celda editable sale de la región y alarga la
    // PÁGINA a 1700 px a 1366 px de ancho, aunque no se vea nada.
    const bloque = /\.silice-hoja__desplazable\s*\{([^}]*)\}/.exec(plano);
    expect(bloque).not.toBeNull();
    expect(bloque![1]).toMatch(/position:\s*relative/);
  });

  test("el foco programado se ve siempre, no solo con el teclado", () => {
    const bloque = /\.silice-plano__resultado\s*\{[\s\S]*?&:focus\s*\{([^}]*)\}/.exec(plano);
    expect(bloque).not.toBeNull();
    expect(bloque![1]).toMatch(/outline:\s*2px solid/);
  });

  test("la zona de soltar archivo mide 96 px (6 rem), regla común", () => {
    expect(comun).toMatch(/block-size:\s*6rem/);
  });
});
