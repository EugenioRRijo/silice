import { describe, expect, test } from "vitest";

// Con `css: false` (vite.config.ts) Vitest entrega vacio el `?raw` de un .scss: se lee el archivo con el modulo de Node.
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const fuente = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/comun/comun.scss`, "utf-8");

// VD-4 (delta de la auditoria visual): el boton del exacto del Historial y los `<summary>` de Control y de la curva
// mostraban el anillo del NAVEGADOR (`outline: auto 1px`, esquinas redondeadas) en vez del de Carbon. jsdom no calcula
// CSS: la regla se lee del fuente y el anillo se midio en el navegador (informe de VD-2).
function reglaDe(selector: string): string | null {
  const i = fuente.indexOf(selector);
  if (i < 0) return null;
  const abre = fuente.indexOf("{", i);
  return fuente.slice(i, fuente.indexOf("}", abre));
}

describe("anillo de foco de Carbon en summary y en el boton del exacto", () => {
  const regla = reglaDe("summary:focus-visible");

  test("hay UNA regla comun que nombra summary y el boton del exacto", () => {
    expect(regla).not.toBeNull();
    expect(regla).toContain(".silice-historial__monto-valor:focus-visible");
  });

  test("el anillo es de 2 px, solido, con el token de foco de Carbon y separado 2 px", () => {
    expect(regla).toMatch(/outline:\s*2px solid var\(--cds-focus\)/);
    expect(regla).toMatch(/outline-offset:\s*2px/);
  });

  test("sin color suelto en la regla", () => {
    expect(regla).not.toMatch(/#[0-9a-fA-F]{3,8}\b|rgb\(/);
  });
});
