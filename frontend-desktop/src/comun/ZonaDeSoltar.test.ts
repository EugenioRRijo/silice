import { describe, expect, test } from "vitest";

// Con `css: false` (vite.config.ts) Vitest entrega vacio el `?raw` de un .scss: se lee el archivo con el modulo de Node
// (sin importar "node:fs", que tsconfig.app no tipa).
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
// Vitest corre con frontend-desktop como carpeta de trabajo.
const fuente = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/comun/comun.scss`, "utf-8");

// VB-2 (auditoria visual del bloque B): jsdom no calcula CSS, asi que la regla se lee del fuente. El mismo boton lleva
// `cds--file__drop-container` y `cds--file-browse-btn`: una regla posterior solo de `.cds--file-browse-btn` con
// `block-size: 100%` anulaba los 6rem y la zona medía 36 px en el navegador (medido). El alto minimo de 96 px (6rem)
// va en UNA regla que nombra las dos clases, y ninguna regla de la zona vuelve a fijar el alto en porcentaje.
function bloque(selector: string): string | null {
  const i = fuente.indexOf(selector + " {");
  if (i < 0) return null;
  return fuente.slice(i, fuente.indexOf("}", i));
}

describe("Zona de soltar archivo: alto de 96 px", () => {
  test("una regla con las dos clases fija block-size y min-block-size en 6rem", () => {
    const regla = bloque(".cds--file__drop-container.cds--file-browse-btn");
    expect(regla).not.toBeNull();
    expect(regla).toMatch(/block-size:\s*6rem/);
    expect(regla).toMatch(/min-block-size:\s*6rem/);
  });

  test("ninguna regla de la zona fija block-size en porcentaje", () => {
    const inicio = fuente.indexOf(".silice-subida {");
    expect(inicio).toBeGreaterThan(-1);
    const zona = fuente.slice(inicio, fuente.indexOf(".silice-descarga {", inicio));
    expect(zona).not.toMatch(/block-size:\s*100%/);
  });
});
