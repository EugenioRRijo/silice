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

// Van en tokens.scss, en un bloque propio `:root, .cds--g10` DESPUÉS del tema de Carbon: la app va envuelta en un div
// .cds--g10 (App.tsx) que Carbon llena con el azul, y a igual especificidad gana la última declaración. No pueden ir en
// el `:root` del tema: allí también se declaran los --silice-*, que la empresa fija en la raíz y no deben repetirse en
// el div. Se lee desde ese bloque hasta el final del archivo.
const tokens = leer("estilos/tokens.scss");
const raiz = tokens.slice(tokens.indexOf(":root, .cds--g10"));
const nuevas = raiz.split("\n").filter((l) => /--(cds-(button-primary|link-primary|border-interactive|text-on-color)|silice-boton-borde)/.test(l));

describe("color de acción de la empresa en toda la aplicación", () => {
  test("las reasignaciones cubren la raíz y la zona .cds--g10 del Theme de la app", () => {
    expect(raiz).toMatch(/^:root,\s*\.cds--g10\s*\{/);
  });

  test("el botón principal en reposo es el acento aclarado con blanco", () => {
    expect(raiz).toMatch(/--cds-button-primary:\s*color-mix\(in srgb,\s*var\(--silice-acento\)\s*#\{\$mezcla-reposo\},\s*white\)/);
  });

  test("al pasar el ratón es el acento al 85 % con blanco y al pulsar, el acento puro", () => {
    expect(raiz).toMatch(/--cds-button-primary-hover:\s*color-mix\(in srgb,\s*var\(--silice-acento\)\s*#\{\$mezcla-hover\},\s*white\)/);
    expect(raiz).toMatch(/--cds-button-primary-active:\s*var\(--silice-acento\);/);
  });

  test("el borde de 1 px del botón mezcla el acento con el marco", () => {
    expect(raiz).toMatch(
      /--silice-boton-borde:\s*color-mix\(in srgb,\s*var\(--silice-acento\)\s*#\{\$mezcla-borde\},\s*var\(--silice-marco\)\)/,
    );
    const regla = reglaDe(tokens, ".cds--btn--primary");
    expect(regla).toMatch(/border-color:\s*var\(--silice-boton-borde\)/);
  });

  test("el texto del botón principal es del color del marco, solo en ese botón", () => {
    expect(reglaDe(tokens, ".cds--btn--primary")).toMatch(/--cds-text-on-color:\s*var\(--silice-marco\)/);
    // En la raíz no: --cds-text-on-color también se usa sobre otros fondos.
    expect(raiz.slice(0, raiz.indexOf(".cds--btn--primary"))).not.toMatch(/--cds-text-on-color/);
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
    expect(nuevas.length).toBeGreaterThanOrEqual(8);
    expect(nuevas.join("\n")).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });
});
