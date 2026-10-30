// @vitest-environment jsdom
import { afterAll, beforeAll, describe, expect, test } from "vitest";
import { compile, Logger } from "sass";

// La app va envuelta en <Theme theme="g10"> (App.tsx): un div.cds--g10 que Carbon llena con SUS valores (azul). Los
// descendientes heredan los de ese div, no los de :root; por eso el color de acción también debe reasignarse ahí. Se
// compila tokens.scss de verdad y se pregunta a la cascada de jsdom, dentro y fuera del div.
const raiz = (globalThis as unknown as { process: { cwd(): string } }).process.cwd();
let css = "";
beforeAll(() => {
  css = compile(`${raiz}/src/estilos/tokens.scss`, { quietDeps: true, logger: Logger.silent, loadPaths: [`${raiz}/node_modules`] }).css;
  const estilo = document.createElement("style");
  estilo.textContent = css;
  document.head.append(estilo);
  document.body.innerHTML = `
    <div id="fuera"><a id="enlace-fuera" class="cds--link" href="#x">a</a><button id="boton-fuera" class="cds--btn cds--btn--primary">b</button><button id="terciario-fuera" class="cds--btn cds--btn--tertiary">t</button></div>
    <div class="cds--g10" id="tema"><a id="enlace" class="cds--link" href="#x">a</a><button id="boton" class="cds--btn cds--btn--primary">b</button><button id="terciario" class="cds--btn cds--btn--tertiary">t</button><button id="secundario" class="cds--btn cds--btn--secondary">s</button><div class="cds--tabs"><button id="pestana" class="cds--tabs__nav-item cds--tabs__nav-item--selected">p</button></div></div>`;
}, 60_000);
afterAll(() => {
  document.head.innerHTML = "";
  document.body.innerHTML = "";
});

// jsdom normaliza los espacios dentro de color-mix(...): se comparan sin ellos.
const sinEspacios = (texto: string) => texto.replace(/\s+/g, "");
const valor = (id: string, variable: string) =>
  sinEspacios(getComputedStyle(document.getElementById(id)!).getPropertyValue(variable));

// Tarea 4c: el botón principal es el complementario con texto blanco; ratón y pulsado lo oscurecen con negro.
const REPOSO = "var(--silice-complementario)";
const HOVER = "color-mix(in srgb, var(--silice-complementario) 85%, black)";
const PULSADO = "color-mix(in srgb, var(--silice-complementario) 70%, black)";

describe("el color de acción llega a los descendientes del tema g10", () => {
  test.each([
    ["boton", "--cds-button-primary", REPOSO],
    ["boton", "--cds-button-primary-hover", HOVER],
    ["boton", "--cds-button-primary-active", PULSADO],
    ["enlace", "--cds-link-primary", "var(--silice-complementario)"],
    ["pestana", "--cds-border-interactive", "var(--silice-complementario)"],
    ["boton-fuera", "--cds-button-primary", REPOSO],
    ["boton-fuera", "--cds-button-primary-hover", HOVER],
    ["boton-fuera", "--cds-button-primary-active", PULSADO],
    ["enlace-fuera", "--cds-link-primary", "var(--silice-complementario)"],
  ])("%s resuelve %s a %s", (id, variable, esperado) => {
    expect(valor(id, variable)).toBe(sinEspacios(esperado));
  });

  // Cierre de F3 (H5): el boton terciario (borde y texto) de Carbon g10 es azul (#0f62fe); pasa al complementario. Al pasar
  // el raton Carbon lo llena y pone el texto en blanco (text-inverse): el fondo es el complementario, que el servidor ya
  // mide contra el blanco (4,5:1), y al pulsar, ese mismo mas oscuro (el blanco se lee aun mejor). El secundario de g10
  // es gris oscuro (#393939), no azul: no se toca.
  test.each([
    ["terciario", "--cds-button-tertiary", "var(--silice-complementario)"],
    ["terciario", "--cds-button-tertiary-hover", "var(--silice-complementario)"],
    ["terciario", "--cds-button-tertiary-active", "color-mix(in srgb, var(--silice-complementario) 75%, black)"],
    ["terciario-fuera", "--cds-button-tertiary", "var(--silice-complementario)"],
    ["terciario-fuera", "--cds-button-tertiary-hover", "var(--silice-complementario)"],
    ["terciario-fuera", "--cds-button-tertiary-active", "color-mix(in srgb, var(--silice-complementario) 75%, black)"],
  ])("%s resuelve %s a %s", (id, variable, esperado) => {
    expect(valor(id, variable)).toBe(sinEspacios(esperado));
  });

  test("el secundario de g10 sigue en el gris de Carbon, sin azul ni color de la empresa", () => {
    for (const variable of ["--cds-button-secondary", "--cds-button-secondary-hover", "--cds-button-secondary-active"]) {
      expect(valor("secundario", variable)).not.toContain("--silice-");
      expect(valor("secundario", variable).toLowerCase()).not.toMatch(/#0f62fe|#0043ce|#002d9c|#0050e6/);
    }
  });

  test("el texto del botón principal vuelve al blanco de Carbon: ya no se reasigna", () => {
    expect(valor("boton", "--cds-text-on-color")).not.toContain("--silice-");
    expect(valor("boton-fuera", "--cds-text-on-color")).not.toContain("--silice-");
    expect(css).not.toMatch(/--cds-text-on-color/);
  });

  test("el botón principal ya no tiene borde propio ni token de borde", () => {
    expect(css).not.toContain("silice-boton-borde");
    expect(valor("boton", "--silice-boton-borde")).toBe("");
    // Ninguna regla propia de .cds--btn--primary toca el borde: queda el transparente de Carbon.
    const propias = [...css.matchAll(/\.cds--btn--primary\s*\{([^}]*)\}/g)].map((m) => m[1]!);
    expect(propias.some((r) => /--silice-/.test(r))).toBe(false);
  });

  test("el acento ya no es relleno de ninguna acción: ningún token --cds-button-* lo usa", () => {
    expect(css).not.toMatch(/--cds-button-[a-z-]+:[^;]*--silice-acento/);
  });

  // WCAG 1.4.1: el enlace va en el complementario, que sin uno propio es el marco (#393939 en el tema neutro: dista
  // 1,57:1 del texto #161616); con otro color la distancia cambia, pero solo se distinguiría por el color;
  // Carbon trae `.cds--link { text-decoration: none }`, así que se subraya.
  test("los enlaces de Carbon van subrayados en reposo", () => {
    expect(getComputedStyle(document.getElementById("enlace")!).getPropertyValue("text-decoration")).toContain("underline");
    expect(getComputedStyle(document.getElementById("enlace-fuera")!).getPropertyValue("text-decoration")).toContain("underline");
  });
});
