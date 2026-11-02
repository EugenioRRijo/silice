import { describe, expect, test } from "vitest";

// jsdom no calcula CSS: las reglas se leen del fuente (como estilosMarco.test.ts). Tarea 4c: el botón principal lleva el
// color complementario con texto blanco (el acento es la marca, no una acción); enlaces, bordes interactivos y la raya de la pestaña activa, el
// color complementario (que sin uno propio sigue al marco; el acento sobre el fondo da ~2:1 y no sirve para texto ni
// bordes). El foco no se toca.
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

// Van en tokens.scss, en un bloque propio `:root, .cds--g10` DESPUÉS del tema de Carbon: la app va envuelta en un div
// .cds--g10 (App.tsx) que Carbon llena con el azul, y a igual especificidad gana la última declaración. No pueden ir en
// el `:root` del tema: allí también se declaran los --silice-*, que la empresa fija en la raíz y no deben repetirse en
// el div. Se lee desde ese bloque hasta el final del archivo.
const tokens = leer("estilos/tokens.scss");
const raiz = tokens.slice(tokens.indexOf(":root, .cds--g10"));
const nuevas = raiz.split("\n").filter((l) => /--cds-(button-primary|link-primary|border-interactive)/.test(l));

describe("color de acción de la empresa en toda la aplicación", () => {
  test("las reasignaciones cubren la raíz y la zona .cds--g10 del Theme de la app", () => {
    expect(raiz).toMatch(/^:root,\s*\.cds--g10\s*\{/);
  });

  test("el botón principal en reposo es el color complementario", () => {
    expect(raiz).toMatch(/--cds-button-primary:\s*var\(--silice-complementario\);/);
  });

  test("al pasar el ratón es el complementario al 85 % con negro y al pulsar, al 70 %", () => {
    expect(raiz).toMatch(/--cds-button-primary-hover:\s*color-mix\(in srgb,\s*var\(--silice-complementario\)\s*#\{\$oscurecido-hover\},\s*black\)/);
    expect(raiz).toMatch(/--cds-button-primary-active:\s*color-mix\(in srgb,\s*var\(--silice-complementario\)\s*#\{\$oscurecido-pulsado\},\s*black\)/);
  });

  test("el botón principal no tiene borde propio ni reasigna el texto sobre color", () => {
    expect(tokens).not.toContain("silice-boton-borde");
    expect(tokens).not.toMatch(/\$mezcla-/);
    expect(tokens).not.toMatch(/--cds-text-on-color/);
    expect(reglaDe(tokens, ".cds--btn--primary")).toBe("");
  });

  test("ningún token de botón usa el acento: el acento es la marca", () => {
    expect(raiz).not.toMatch(/--cds-button-[a-z-]+:[^;]*--silice-acento/);
  });

  test("enlaces, bordes interactivos y la raya de la pestaña activa son del color complementario", () => {
    expect(raiz).toMatch(/--cds-link-primary:\s*var\(--silice-complementario\)/);
    expect(raiz).toMatch(/--cds-link-primary-hover:\s*var\(--silice-complementario\)/);
    // La raya de la pestaña seleccionada de Carbon usa --cds-border-interactive.
    expect(raiz).toMatch(/--cds-border-interactive:\s*var\(--silice-complementario\)/);
  });

  test("los tokens nuevos del tema tienen su neutro en la raíz", () => {
    expect(tokens).toMatch(/--silice-complementario:\s*var\(--silice-marco\)/);
    expect(tokens).toMatch(/--silice-contador-numero:\s*var\(--silice-marco\)/);
    expect(tokens).toMatch(/--silice-contador-fondo:\s*var\(--silice-lateral\)/);
  });

  test("el foco no se reasigna", () => {
    expect(tokens).not.toMatch(/--cds-focus(-inverse)?\s*:/);
    expect(leer("marco/marco.scss")).not.toMatch(/--cds-focus(-inverse)?\s*:/);
  });

  test("ninguna regla nueva lleva hexadecimales sueltos", () => {
    expect(nuevas.length).toBeGreaterThanOrEqual(6);
    expect(nuevas.join("\n")).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });
});
