import { describe, expect, test } from "vitest";

// jsdom no calcula CSS: las reglas se leen del fuente (como estilosMarco.test.ts). D-F3-4: el botón principal lleva el
// acento de la empresa con texto del color del marco; enlaces, bordes interactivos y la raya de la pestaña activa, el
// color del marco (el ámbar sobre el fondo da ~2:1 y no sirve para texto ni bordes). El foco no se toca.
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

const marco = leer("marco/marco.scss");
// Los diálogos se montan fuera de .silice-marco (portal en el body), así que las reasignaciones van en la raíz.
const raiz = reglaDe(marco, ":root");

describe("color de acción de la empresa bajo el marco", () => {
  test("el botón principal toma el acento", () => {
    expect(raiz).toMatch(/--cds-button-primary:\s*var\(--silice-acento\)/);
  });

  test("hover y active derivan del acento hacia el marco, sin hexadecimales", () => {
    expect(raiz).toMatch(
      /--cds-button-primary-hover:\s*color-mix\(in srgb,\s*var\(--silice-acento\)\s*85%,\s*var\(--silice-marco\)\)/,
    );
    expect(raiz).toMatch(
      /--cds-button-primary-active:\s*color-mix\(in srgb,\s*var\(--silice-acento\)\s*80%,\s*var\(--silice-marco\)\)/,
    );
  });

  test("el texto del botón principal es del color del marco, solo en ese botón", () => {
    expect(reglaDe(marco, ".cds--btn--primary")).toMatch(/--cds-text-on-color:\s*var\(--silice-marco\)/);
    expect(raiz).not.toMatch(/--cds-text-on-color/);
  });

  test("enlaces, bordes interactivos y la raya de la pestaña activa son del color del marco", () => {
    expect(raiz).toMatch(/--cds-link-primary:\s*var\(--silice-marco\)/);
    expect(raiz).toMatch(/--cds-link-primary-hover:\s*var\(--silice-marco\)/);
    // La raya de la pestaña seleccionada de Carbon usa --cds-border-interactive.
    expect(raiz).toMatch(/--cds-border-interactive:\s*var\(--silice-marco\)/);
  });

  test("el foco no se reasigna", () => {
    expect(marco).not.toMatch(/--cds-focus\s*:/);
    expect(marco).not.toMatch(/--cds-focus-inverse\s*:/);
  });

  test("ninguna regla nueva lleva hexadecimales sueltos", () => {
    expect(raiz).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
    expect(reglaDe(marco, ".cds--btn--primary")).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });
});
