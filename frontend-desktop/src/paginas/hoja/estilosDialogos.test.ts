import { describe, expect, test } from "vitest";

// Con `css: false` el `?raw` de un .scss llega vacío: se lee con el módulo de Node (como estilosEdicion.test.ts).
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const estilos = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/paginas/hoja/hoja.scss`, "utf-8");

function bloque(selector: string): string {
  const inicio = estilos.indexOf(`${selector} {`);
  expect(inicio, `falta la regla ${selector}`).toBeGreaterThanOrEqual(0);
  return estilos.slice(inicio, estilos.indexOf("\n}\n", inicio));
}

// 3e-3, H-4: «Registrar una cotización» medía 692 de 768 px y Cancelar/Cotizar quedaban bajo el borde. El pie de acciones va
// fijo (sticky) en el borde inferior del diálogo y el cuerpo se desplaza; jsdom no calcula el diseño, así que aquí se
// comprueba que las reglas estén escritas y la medición real es la de la auditoría visual.
describe("estilos de los diálogos de la Hoja (H-4)", () => {
  test("el diálogo cabe en la ventana (viewport dinámico) y desplaza por dentro", () => {
    const b = bloque(".silice-hoja__dialogo");
    expect(b).toMatch(/max-block-size:\s*calc\(100dvh\s*-\s*2rem\)/);
    expect(b).toMatch(/overflow-y:\s*auto/);
  });

  test("el pie de acciones queda fijo al borde inferior, con fondo opaco para no mostrar lo que pasa debajo", () => {
    const b = bloque(".silice-hoja__dialogo > .silice-hoja__acciones:last-child");
    expect(b).toMatch(/position:\s*sticky/);
    expect(b).toMatch(/inset-block-end:\s*0/);
    expect(b).toMatch(/background:\s*var\(--cds-layer/);
  });

  test("las variantes no vuelven a fijar el alto en vh (el de la base manda)", () => {
    expect(bloque(".silice-hoja__dialogo--guardar")).not.toMatch(/max-block-size/);
    expect(bloque(".silice-hoja__dialogo--operacion")).not.toMatch(/max-block-size/);
  });
});
