import { describe, expect, test } from "vitest";
import { ROTULOS_DE_COLUMNA } from "./rotulosDeColumna";

// Contrato con el servidor: los rótulos de las columnas del metraje son los de `ROTULOS_DE_COLUMNA` en
// aplicacion/hoja.py. Se lee ese archivo como texto (con el módulo de Node, porque Vitest corre en jsdom) y se compara
// tabla por tabla, clave por clave y en el mismo orden (el resumen de una fila sigue el orden de las columnas).
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const python = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/../aplicacion/hoja.py`, "utf-8");

function rotulosDelServidor(): Record<string, [string, string][]> {
  const inicio = python.indexOf("ROTULOS_DE_COLUMNA: dict[str, dict[str, str]] = {");
  const fin = inicio + python.slice(inicio).search(/\r?\n}\r?\n/);
  const bloque = python.slice(inicio, fin);
  const tablas: Record<string, [string, string][]> = {};
  let actual = "";
  for (const linea of bloque.split(/\r?\n/)) {
    const abre = /^ {4}"(\w+)": \{(.*)$/.exec(linea);
    if (abre) {
      actual = abre[1]!;
      tablas[actual] = [];
      for (const m of abre[2]!.matchAll(/"(\w+)": "([^"]*)"/g)) tablas[actual]!.push([m[1]!, m[2]!]);
      continue;
    }
    const par = /^\s+"(\w+)": "([^"]*)",?$/.exec(linea);
    if (par && actual) tablas[actual]!.push([par[1]!, par[2]!]);
  }
  return tablas;
}

describe("rótulos de las columnas del metraje", () => {
  test("coinciden con los de aplicacion/hoja.py (ROTULOS_DE_COLUMNA), en el mismo orden", () => {
    const servidor = rotulosDelServidor();
    expect(Object.keys(servidor)).toEqual(["origenes", "ambientes", "fuentes", "puntos", "tramos"]);
    const propios = Object.fromEntries(Object.entries(ROTULOS_DE_COLUMNA).map(([t, cols]) => [t, Object.entries(cols)]));
    expect(propios).toEqual(servidor);
  });

  test("la columna «id» se rotula «Código», como en el servidor", () => {
    expect(ROTULOS_DE_COLUMNA.puntos!.id).toBe("Código");
  });
});
