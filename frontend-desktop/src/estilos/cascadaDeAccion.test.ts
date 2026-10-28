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
    <div id="fuera"><a id="enlace-fuera" class="cds--link" href="#x">a</a><button id="boton-fuera" class="cds--btn cds--btn--primary">b</button></div>
    <div class="cds--g10" id="tema"><a id="enlace" class="cds--link" href="#x">a</a><button id="boton" class="cds--btn cds--btn--primary">b</button><div class="cds--tabs"><button id="pestana" class="cds--tabs__nav-item cds--tabs__nav-item--selected">p</button></div></div>`;
}, 60_000);
afterAll(() => {
  document.head.innerHTML = "";
  document.body.innerHTML = "";
});

// jsdom normaliza los espacios dentro de color-mix(...): se comparan sin ellos.
const sinEspacios = (texto: string) => texto.replace(/\s+/g, "");
const valor = (id: string, variable: string) =>
  sinEspacios(getComputedStyle(document.getElementById(id)!).getPropertyValue(variable));

const REPOSO = "color-mix(in srgb, var(--silice-acento) 55%, white)";
const HOVER = "color-mix(in srgb, var(--silice-acento) 85%, white)";
const BORDE = "color-mix(in srgb, var(--silice-acento) 50%, var(--silice-marco))";

describe("el color de acción llega a los descendientes del tema g10", () => {
  test.each([
    ["boton", "--cds-button-primary", REPOSO],
    ["boton", "--cds-button-primary-hover", HOVER],
    ["boton", "--cds-button-primary-active", "var(--silice-acento)"],
    ["boton", "--silice-boton-borde", BORDE],
    ["enlace", "--cds-link-primary", "var(--silice-complementario)"],
    ["pestana", "--cds-border-interactive", "var(--silice-complementario)"],
    ["boton-fuera", "--cds-button-primary", REPOSO],
    ["boton-fuera", "--cds-button-primary-hover", HOVER],
    ["boton-fuera", "--cds-button-primary-active", "var(--silice-acento)"],
    ["boton-fuera", "--silice-boton-borde", BORDE],
    ["enlace-fuera", "--cds-link-primary", "var(--silice-complementario)"],
  ])("%s resuelve %s a %s", (id, variable, esperado) => {
    expect(valor(id, variable)).toBe(sinEspacios(esperado));
  });

  test("el texto del botón principal es del marco, y el de otros fondos no se toca", () => {
    expect(valor("boton", "--cds-text-on-color")).toBe("var(--silice-marco)");
    expect(valor("enlace", "--cds-text-on-color")).not.toBe("var(--silice-marco)");
  });

  test("el botón principal pinta su borde de 1 px con el borde mezclado, dentro y fuera del div", () => {
    // jsdom no resuelve var() dentro de border-color: se lee la regla compilada, que vale para los dos botones.
    const regla = /\.cds--btn--primary\s*\{([^}]*)\}/g;
    const propias = [...css.matchAll(regla)].map((m) => m[1]!).filter((r) => r.includes("--silice-boton-borde"));
    expect(propias.some((r) => /border-color:\s*var\(--silice-boton-borde\)/.test(r))).toBe(true);
    // Carbon pone el ancho de 1 px y el estilo sólido en el mismo botón; aquí solo cambia el color.
    expect(css).toMatch(/\.cds--btn--primary\s*\{[^}]*border-width:\s*1px;\s*border-style:\s*solid/);
  });

  test("la regla propia del borde va DESPUÉS de la de Carbon (misma especificidad: gana la última)", () => {
    const reglas = [...css.matchAll(/\.cds--btn--primary\s*\{([^}]*)\}/g)];
    const deCarbon = reglas.find((m) => /border-color:\s*transparent/.test(m[1]!));
    const propia = reglas.find((m) => /border-color:\s*var\(--silice-boton-borde\)/.test(m[1]!));
    expect(deCarbon).toBeDefined();
    expect(propia).toBeDefined();
    expect(propia!.index).toBeGreaterThan(deCarbon!.index);
  });

  // WCAG 1.4.1: el enlace va en el complementario, que sin uno propio es el marco (#393939 en el tema neutro: dista
  // 1,57:1 del texto #161616); con otro color la distancia cambia, pero solo se distinguiría por el color;
  // Carbon trae `.cds--link { text-decoration: none }`, así que se subraya.
  test("los enlaces de Carbon van subrayados en reposo", () => {
    expect(getComputedStyle(document.getElementById("enlace")!).getPropertyValue("text-decoration")).toContain("underline");
    expect(getComputedStyle(document.getElementById("enlace-fuera")!).getPropertyValue("text-decoration")).toContain("underline");
  });
});
