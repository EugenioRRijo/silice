import { gray, warmGray, yellow } from "@carbon/colors";
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

  it("lleva exactamente las siete claves que mide", () => {
    expect(Object.keys(servidor).sort()).toEqual(
      ["acento", "borde", "lateral", "lateral-activo", "marco", "texto", "texto-del-marco"].sort(),
    );
  });

  it.each([
    ["marco", () => gray[80], "gray-80 de @carbon/colors"],
    ["acento", () => yellow[30], "yellow-30 de @carbon/colors"],
    ["lateral", () => warmGray[10], "warm-gray-10 de @carbon/colors"],
    ["lateral-activo", () => warmGray[20], "warm-gray-20 de @carbon/colors"],
    ["borde", () => gray[50], "gray-50 de @carbon/colors"],
    ["texto-del-marco", () => g10["textInverse"]!, "text-inverse del tema g10 de @carbon/themes"],
    ["texto", () => g10["textPrimary"]!, "text-primary del tema g10 de @carbon/themes"],
  ])("%s coincide con %s", (clave, deCarbon) => {
    expect(servidor[clave]).toBe(deCarbon().toLowerCase());
  });

  it("el marco neutro es el fondo inverso del tema g10 (--silice-marco = --cds-background-inverse)", () => {
    expect(servidor["marco"]).toBe(g10["backgroundInverse"]!.toLowerCase());
    expect(servidor["borde"]).toBe(g10["borderStrong01"]!.toLowerCase());
  });
});
