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

// Van en tokens.scss, dentro del mismo `:root` que el tema de Carbon y después de él: en el CSS compilado marco.scss sale
// ANTES que el tema, y a igual especificidad la última declaración gana (medido en dist/ con npm run build). Ese bloque
// lleva interpolaciones `#{...}`, así que se lee desde `:root {` hasta el final del archivo.
const tokens = leer("estilos/tokens.scss");
const raiz = tokens.slice(tokens.indexOf(":root"));
const nuevas = raiz.split("\n").filter((l) => /--cds-(button-primary|link-primary|border-interactive|text-on-color)/.test(l));

describe("color de acción de la empresa en toda la aplicación", () => {
  test("las reasignaciones cubren la raíz y la zona .cds--g10 del Theme de la app", () => {
    expect(raiz).toMatch(/^:root,\s*\.cds--g10\s*\{/);
  });

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
    expect(reglaDe(tokens, ".cds--btn--primary")).toMatch(/--cds-text-on-color:\s*var\(--silice-marco\)/);
    // En la raíz no: --cds-text-on-color también se usa sobre otros fondos.
    expect(raiz.slice(0, raiz.indexOf(".cds--btn--primary"))).not.toMatch(/--cds-text-on-color/);
  });

  test("enlaces, bordes interactivos y la raya de la pestaña activa son del color del marco", () => {
    expect(raiz).toMatch(/--cds-link-primary:\s*var\(--silice-marco\)/);
    expect(raiz).toMatch(/--cds-link-primary-hover:\s*var\(--silice-marco\)/);
    // La raya de la pestaña seleccionada de Carbon usa --cds-border-interactive.
    expect(raiz).toMatch(/--cds-border-interactive:\s*var\(--silice-marco\)/);
  });

  test("el foco no se reasigna", () => {
    expect(tokens).not.toMatch(/--cds-focus(-inverse)?\s*:/);
    expect(leer("marco/marco.scss")).not.toMatch(/--cds-focus(-inverse)?\s*:/);
  });

  test("ninguna regla nueva lleva hexadecimales sueltos", () => {
    expect(nuevas.length).toBeGreaterThanOrEqual(7);
    expect(nuevas.join("\n")).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });
});
