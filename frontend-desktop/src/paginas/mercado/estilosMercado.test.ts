import { describe, expect, test } from "vitest";

// MOD-5a (D-4): a 1056 px con letra Grande y Muy grande, el campo «Fecha» de «Anotar una observación» salía de su columna
// y la página se desplazaba a lo ancho. jsdom no mide el diseño: se lee la hoja de estilo, como `estilosLetra.test.ts`.
// La regla: ninguna rejilla exige una columna más ancha que su contenedor y sus campos pueden encogerse dentro de ella.
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }).process;
const scss = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/paginas/mercado/mercado.scss`, "utf-8");

// El bloque `{ ... }` (con sus anidados) que sigue al primer selector que contiene `selector`.
function bloque(selector: string): string {
  const inicio = scss.indexOf(selector);
  expect(inicio, selector).toBeGreaterThanOrEqual(0);
  const abre = scss.indexOf("{", inicio);
  let nivel = 0;
  for (let i = abre; i < scss.length; i++) {
    if (scss[i] === "{") nivel += 1;
    if (scss[i] === "}") nivel -= 1;
    if (nivel === 0) return scss.slice(abre, i + 1);
  }
  throw new Error(`Bloque sin cerrar: ${selector}`);
}

describe("estudio de mercado sin desplazamiento horizontal (letra Grande y Muy grande)", () => {
  test("toda columna de rejilla con mínimo cede al ancho del contenedor: minmax(min(100%, …), …) o minmax(0, …)", () => {
    const minimos = [...scss.matchAll(/minmax\(\s*([^,]+?)\s*,/g)].map((m) => m[1]);
    expect(minimos.length).toBeGreaterThan(0);
    // El mínimo capturado llega hasta la primera coma: «min(100%» (de «minmax(min(100%, 14rem), 1fr)») o «0».
    const fijos = minimos.filter((m) => !/^min\(\s*100%$/.test(m) && m !== "0");
    expect(fijos).toEqual([]);
  });

  test("en los formularios «Su precio» y «Anotar una observación» los campos (fecha incluida) se encogen con su columna", () => {
    const formularios = bloque(".silice-mercado__usar,");
    expect(formularios).toMatch(/\.cds--form-item[^{]*\{[^}]*min-inline-size:\s*0/);
    expect(formularios).toMatch(/(?:input|\.cds--text-input)[^{]*\{[^}]*min-inline-size:\s*0/);
    expect(formularios).toMatch(/(?:input|\.cds--text-input)[^{]*\{[^}]*max-inline-size:\s*100%/);
  });
});
