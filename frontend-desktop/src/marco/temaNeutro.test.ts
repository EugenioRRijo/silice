import { describe, expect, it } from "vitest";

// El servidor mide los avisos de contraste contra una copia de los colores neutros (`_NEUTRO` en aplicacion/tema.py); la
// copia debe coincidir con los paquetes de Carbon de los que sale (tokens.scss usa @carbon/colors y el tema g10). Se lee
// con Node: con `css: false` los .scss no llegan a las pruebas, y el .py tampoco es un módulo del front.
interface Nodo {
  cwd(): string;
  getBuiltinModule(nombre: "node:fs"): { readFileSync(ruta: string, codificacion: string): string };
  getBuiltinModule(nombre: "node:module"): { createRequire(desde: string): (modulo: string) => unknown };
}
const nodo = (globalThis as unknown as { process: Nodo }).process;
const raiz = nodo.cwd();

function neutroDelServidor(): Record<string, string> {
  const fuente = nodo.getBuiltinModule("node:fs").readFileSync(`${raiz}/../aplicacion/tema.py`, "utf-8");
  const bloque = /_NEUTRO = \{([^}]*)\}/.exec(fuente)?.[1] ?? "";
  return Object.fromEntries([...bloque.matchAll(/"([a-z-]+)": "(#[0-9a-f]{6})"/g)].map((m) => [m[1]!, m[2]!]));
}

const g10 = (nodo.getBuiltinModule("node:module").createRequire(`${raiz}/`)("@carbon/themes") as { g10: Record<string, string> }).g10;

describe("_NEUTRO de aplicacion/tema.py frente a Carbon", () => {
  const servidor = neutroDelServidor();

  it("lleva exactamente las diez claves que mide", () => {
    expect(Object.keys(servidor).sort()).toEqual(
      ["acento", "blanco", "borde", "fondo", "lateral", "lateral-activo", "marco", "texto", "texto-del-boton", "texto-del-marco"].sort(),
    );
  });

  const tokens = nodo.getBuiltinModule("node:fs").readFileSync(`${raiz}/src/estilos/tokens.scss`, "utf-8");
  const deTokens = (nombre: string) => new RegExp(`${nombre}:\\s*(#[0-9a-fA-F]{6});`).exec(tokens)![1]!;
  it.each([
    ["marco", () => deTokens("--silice-petroleo"), "--silice-petroleo de tokens.scss"],
    ["acento", () => deTokens("--silice-arena"), "--silice-arena de tokens.scss"],
    ["lateral", () => deTokens("--silice-lateral-base"), "--silice-lateral-base de tokens.scss"],
    ["lateral-activo", () => deTokens("--silice-lateral-hover"), "--silice-lateral-hover de tokens.scss"],
    ["texto-del-boton", () => g10["textOnColor"]!, "text-on-color del tema g10 de @carbon/themes"],
    ["texto-del-marco", () => g10["textInverse"]!, "text-inverse del tema g10 de @carbon/themes"],
    ["texto", () => g10["textPrimary"]!, "text-primary del tema g10 de @carbon/themes"],
    ["fondo", () => g10["background"]!, "background del tema g10 de @carbon/themes"],
    ["blanco", () => g10["layer01"]!, "layer-01 del tema g10 de @carbon/themes"],
  ])("%s coincide con %s", (clave, deCarbon) => {
    expect(servidor[clave]).toBe(deCarbon().toLowerCase());
  });

  it("el borde neutro llega a 3:1 sobre el lateral y sobre el marco (WCAG 1.4.11)", () => {
    const luz = (hex: string) => {
      const [r, g, b] = [1, 3, 5].map((i) => {
        const c = parseInt(hex.slice(i, i + 2), 16) / 255;
        return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
    };
    const razon = (x: string, y: string) => (Math.max(luz(x), luz(y)) + 0.05) / (Math.min(luz(x), luz(y)) + 0.05);
    expect(razon(servidor["borde"]!, servidor["lateral"]!)).toBeGreaterThanOrEqual(3);
    expect(razon(servidor["borde"]!, servidor["marco"]!)).toBeGreaterThanOrEqual(3);
  });
});

// Las proporciones con que el botón principal se oscurece (ratón y pulsado) viven una vez en cada lado:
// OSCURECIDO_DEL_BOTON en aplicacion/tema.py y $oscurecido-* en tokens.scss. El servidor mide el contraste con las
// mismas que pinta el CSS.
describe("las proporciones del botón son las mismas en el servidor y en el SCSS", () => {
  const leerTexto = (ruta: string) => nodo.getBuiltinModule("node:fs").readFileSync(`${raiz}/${ruta}`, "utf-8");
  const python = leerTexto("../aplicacion/tema.py");
  const bloque = /OSCURECIDO_DEL_BOTON = \{([^}]*)\}/.exec(python)?.[1] ?? "";
  const delServidor = Object.fromEntries([...bloque.matchAll(/"([a-z]+)": (\d+)/g)].map((m) => [m[1]!, Number(m[2])]));
  const scss = leerTexto("src/estilos/tokens.scss");
  const delScss = Object.fromEntries([...scss.matchAll(/^\$oscurecido-([a-z]+): (\d+)%;/gm)].map((m) => [m[1]!, Number(m[2])]));

  it("hay dos y coinciden", () => {
    expect(delServidor).toEqual({ hover: 85, pulsado: 70 });
    expect(delScss).toEqual(delServidor);
  });

  it("el SCSS las usa en los tokens del botón, sin números sueltos, y ya no hay mezclas con blanco", () => {
    expect(scss).toContain("var(--silice-complementario) #{$oscurecido-hover}, black");
    expect(scss).toContain("var(--silice-complementario) #{$oscurecido-pulsado}, black");
    expect(scss).not.toMatch(/\$mezcla-/);
    expect(python).not.toContain("MEZCLAS");
  });
});
