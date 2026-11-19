import { describe, expect, test } from "vitest";

// VD-5 (auditoría visual, delta integrada): `TablaDensa` pone el valor CRUDO de una columna con `presentar` en el `title` de la
// celda. Para una fecha eso deja «2026-01-01» en el tooltip bajo «01/01/2026». Las columnas de fecha usan `celda:` (que no
// pone `title`) y el `title` queda para las cifras, que sí llevan su exacto. Esta guardia mira las definiciones de columnas de
// todo el front de una vez (una prueba por pantalla no vería la pantalla que se agregue mañana).
interface Fs {
  readdirSync(ruta: string, opciones: { recursive: true }): string[];
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }).process;
const fs = nodo.getBuiltinModule("node:fs");
const RAIZ = `${nodo.cwd()}/src`;

// `presentar: fechaEsVe`, `presentar: fechaCorta`, `presentar: (v) => fechaDeRanura(v)`…, en la misma definición de columna.
const FECHA_CON_PRESENTAR = /presentar:\s*[^,}\n]*[Ff]echa/;

describe("las columnas de fecha de las tablas no ponen la fecha ISO en el title (VD-5)", () => {
  test("ninguna definición de columna usa `presentar` con un formateador de fecha", () => {
    const fuentes = fs
      .readdirSync(RAIZ, { recursive: true })
      .map((ruta) => ruta.replaceAll("\\", "/"))
      .filter((ruta) => /\.tsx?$/.test(ruta) && !/\.test\.tsx?$/.test(ruta));
    expect(fuentes.length).toBeGreaterThan(100); // la guardia de verdad recorre el front
    const infractores = fuentes.flatMap((ruta) =>
      fs
        .readFileSync(`${RAIZ}/${ruta}`, "utf-8")
        .split("\n")
        .flatMap((linea, i) => (FECHA_CON_PRESENTAR.test(linea) ? [`${ruta}:${i + 1}`] : [])),
    );
    expect(infractores).toEqual([]);
  });
});
