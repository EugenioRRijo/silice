import { compile } from "sass";
import { describe, expect, test } from "vitest";

// D-1 de MOD-5a (navegador real, 2026-10-26): los botones con texto del lado derecho de la barra (la obra, la marca de la
// demostración y la cuenta) declaraban `inline-size: auto` con un solo nombre de clase, pero llevan tambien
// `cds--header__action`, cuya regla de Carbon (`inline-size: 3rem; padding: 0`) tiene la misma especificidad y va DESPUES
// en el CSS compilado (`dist/assets/index-*.css`): ganaba Carbon y el boton medía 3 rem («O…», «A.», la marca encima del
// selector).
//
// jsdom no aplica la cascada de un CSS de verdad. La prueba más fiel que cabe aquí: compilar el SCSS real de cada
// componente con `sass` (el mismo compilador de Vite), ponerle DETRÁS la regla de Carbon (copiada de
// `@carbon/styles/scss/components/ui-shell/header/_header.scss`, `.cds--header__action`, tal como sale en el bundle) y
// resolver la cascada para el botón y su envoltorio: gana la declaración de mayor especificidad y, a igualdad, la
// última. Lo que se mide en el navegador (el ancho en píxeles) lo vuelve a medir MOD-5 con Playwright.

interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }).process;
const fs = nodo.getBuiltinModule("node:fs");
const raiz = `${nodo.cwd()}/src/shell`;

const CARBON = ".cds--header__action { inline-size: 3rem; padding: 0; display: inline-flex; }";

interface Regla {
  selector: string;
  declaraciones: Record<string, string>;
  orden: number;
}

// Las reglas de primer nivel del CSS compilado (las de `@media` y `:root[...]` se dejan: no cambian el ancho del botón).
function reglas(css: string, desde = 0): Regla[] {
  const sinMedia = css.replace(/@media[^{]*\{(?:[^{}]*\{[^}]*\})*[^}]*\}/g, "");
  const salida: Regla[] = [];
  let orden = desde;
  for (const m of sinMedia.matchAll(/([^{}]+)\{([^}]*)\}/g)) {
    const declaraciones: Record<string, string> = {};
    for (const d of m[2]!.split(";")) {
      const [prop, ...valor] = d.split(":");
      if (prop && valor.length) declaraciones[prop.trim()] = valor.join(":").trim();
    }
    for (const selector of m[1]!.split(",")) salida.push({ selector: selector.trim(), declaraciones, orden: orden++ });
  }
  return salida;
}

// Especificidad de un selector de clases y combinador descendiente: (clases, elementos). Sin ids ni pseudoclases aquí.
function especificidad(selector: string): [number, number] {
  const clases = (selector.match(/\.[\w-]+/g) ?? []).length;
  const elementos = selector.split(/\s+/).filter((c) => /^[a-z]/i.test(c)).length;
  return [clases, elementos];
}

// ¿El selector toca al botón (con sus clases) dentro de su envoltorio (con las suyas)?
function toca(selector: string, boton: string[], envoltorio: string[]): boolean {
  if (/[:[>+~]/.test(selector)) return false;
  const partes = selector.split(/\s+/);
  const clasesDe = (parte: string) => (parte.match(/\.[\w-]+/g) ?? []).map((c) => c.slice(1));
  const ultima = clasesDe(partes[partes.length - 1]!);
  if (ultima.length === 0 || !ultima.every((c) => boton.includes(c))) return false;
  return partes.slice(0, -1).every((p) => clasesDe(p).every((c) => envoltorio.includes(c)));
}

// El valor que gana para `propiedad` en el botón.
function ganadora(lista: Regla[], propiedad: string, boton: string[], envoltorio: string[]): string | undefined {
  const candidatas = lista.filter((r) => propiedad in r.declaraciones && toca(r.selector, boton, envoltorio));
  candidatas.sort((a, b) => {
    const [ca, ea] = especificidad(a.selector);
    const [cb, eb] = especificidad(b.selector);
    return ca - cb || ea - eb || a.orden - b.orden;
  });
  return candidatas.at(-1)?.declaraciones[propiedad];
}

// Para `padding: 0` de Carbon frente a `padding-inline` propio: el lado izquierdo efectivo.
function rellenoIzquierdo(lista: Regla[], boton: string[], envoltorio: string[]): string | undefined {
  const candidatas = lista.filter(
    (r) => ("padding" in r.declaraciones || "padding-inline" in r.declaraciones) && toca(r.selector, boton, envoltorio),
  );
  candidatas.sort((a, b) => {
    const [ca, ea] = especificidad(a.selector);
    const [cb, eb] = especificidad(b.selector);
    return ca - cb || ea - eb || a.orden - b.orden;
  });
  const ultima = candidatas.at(-1);
  return ultima?.declaraciones["padding-inline"] ?? ultima?.declaraciones["padding"];
}

const BOTONES = [
  { archivo: "SelectorObra.scss", envoltorio: "silice-obra", boton: "silice-obra__boton" },
  { archivo: "MarcaDemostracion.scss", envoltorio: "silice-demo", boton: "silice-demo__boton" },
  { archivo: "MenuCuenta.scss", envoltorio: "silice-cuenta", boton: "silice-cuenta__boton" },
];

describe("botones con texto de la barra: el ancho es el de su contenido, no los 3 rem de Carbon (D-1 de MOD-5a)", () => {
  test("el resolutor de la prueba ve ganar a Carbon con un solo nombre de clase (el defecto medido)", () => {
    const lista = [...reglas(".x__boton { inline-size: auto; }"), ...reglas(CARBON, 100)];
    expect(ganadora(lista, "inline-size", ["cds--header__action", "x__boton"], ["x"])).toBe("3rem");
  });

  test.each(BOTONES)("$archivo: gana su inline-size auto y su relleno lateral", ({ archivo, envoltorio, boton }) => {
    const css = compile(`${raiz}/${archivo}`, { style: "expanded" }).css;
    const lista = [...reglas(css), ...reglas(CARBON, 10_000)];
    const clases = ["cds--header__action", boton];
    expect(ganadora(lista, "inline-size", clases, [envoltorio])).toBe("auto");
    expect(ganadora(lista, "display", clases, [envoltorio])).toBe("flex");
    expect(rellenoIzquierdo(lista, clases, [envoltorio])).toBe("0.75rem");
  });

  test("ningún archivo lo resuelve con !important", () => {
    for (const { archivo } of BOTONES) expect(fs.readFileSync(`${raiz}/${archivo}`, "utf-8")).not.toMatch(/!important/);
  });
});
