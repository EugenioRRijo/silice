import { describe, expect, test } from "vitest";

// Con `css: false` el `?raw` de un .scss llega vacío: se lee con el módulo de Node (como estilosEdicion.test.ts).
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const plano = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/paginas/archivos/plano.scss`, "utf-8");
const hoja = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/paginas/hoja/hoja.scss`, "utf-8");
const archivos = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/paginas/archivos/archivos.scss`, "utf-8");
const comun = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/comun/comun.scss`, "utf-8");

// jsdom no calcula el diseño: aquí solo se comprueba que las reglas estén escritas; el efecto se MIDE en navegador (3e-F5).
describe("estilos del flujo Importar plano (3e-2)", () => {
  test("las regiones desplazables contienen a sus descendientes absolutos (las etiquetas ocultas de Carbon)", () => {
    // Sin esto, la etiqueta `cds--visually-hidden` (position: absolute) de cada celda editable sale de la región y alarga la
    // PÁGINA a 1700 px a 1366 px de ancho, aunque no se vea nada.
    // La regla vive con la base de la región desplazable (hoja.scss), no en la hoja del plano: corrige todas las pestañas.
    const bloque = /\.silice-hoja__desplazable\s*\{([^}]*)\}/.exec(hoja);
    expect(bloque).not.toBeNull();
    expect(bloque![1]).toMatch(/position:\s*relative/);
    expect(plano).not.toMatch(/\.silice-hoja__desplazable\s*\{/);
  });

  test("el foco programado se ve siempre, no solo con el teclado", () => {
    const bloque = /\.silice-plano__resultado\s*\{[\s\S]*?&:focus\s*\{([^}]*)\}/.exec(plano);
    expect(bloque).not.toBeNull();
    expect(bloque![1]).toMatch(/outline:\s*2px solid/);
  });

  test("la zona de soltar archivo mide 96 px (6 rem), regla común", () => {
    expect(comun).toMatch(/block-size:\s*6rem/);
  });

  // Menor 1 del árbitro de la Tarea 11 (cierre de F4): el diálogo «Subir plano o cómputo» no es de peligro. Sin esto hereda
  // el borde rojo de `.silice-hoja__dialogo` (hoja.scss), como «Guardar versión» y las operaciones, que lo cambian.
  test("el diálogo de subir lleva el borde de acción, no el rojo de peligro", () => {
    const bloque = /\.silice-hoja__dialogo\.silice-archivos__dialogo\s*\{([^}]*)\}/.exec(archivos);
    expect(bloque).not.toBeNull();
    expect(bloque![1]).toMatch(/border-inline-start-color:\s*var\(--silice-interactivo/);
  });
});
