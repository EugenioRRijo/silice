import { fileURLToPath } from "node:url";
import * as sass from "sass";
import { describe, expect, test } from "vitest";

// Pulido F5, Tarea 3 (H10 de la pasada de navegador del cierre de F4): «Aprobar una versión» medía 1576 px a 1056 y a
// 1366 con letra «Muy grande». La misma causa que H4 en Mercado: una rejilla sin columna declarada toma el ancho mínimo
// de lo más ancho (la tabla de partidas) y la página se desplaza a lo ancho. Con una sola columna que cede, la tabla se
// desplaza en su propia caja (`.silice-tabla`, `overflow-x: auto`) y la página nunca. jsdom no dibuja: se compila el SCSS
// real y se leen sus reglas. La ruta va en una variable, como en `componer/estilosComponer.test.ts`.
const compilar = (ruta: string) => sass.compile(fileURLToPath(new URL(ruta, import.meta.url))).css;
const css = compilar("./aprobar.scss");

// Cada regla de primer nivel del CSS compilado: su selector y su cuerpo.
const reglas = [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map((m) => ({ selector: m[1].trim(), cuerpo: m[2] }));
const rejillas = reglas.filter((r) => /display:\s*grid/.test(r.cuerpo));

describe("«Aprobar una versión» sin desplazamiento horizontal con letra «Muy grande» (H10)", () => {
  test("la página y sus bloques son rejillas", () => {
    const selectores = rejillas.flatMap((r) => r.selector.split(/\s*,\s*/));
    for (const s of [".silice-aprobar", ".silice-aprobar__envio", ".silice-aprobar__panel", ".silice-aprobar__lista", ".silice-aprobar__rastro"]) {
      expect(selectores, s).toContain(s);
    }
  });

  test("toda rejilla de la página es una columna que cede al ancho de la ventana: minmax(0, 1fr)", () => {
    const sinColumna = rejillas.filter((r) => !/grid-template-columns:\s*minmax\(0, 1fr\)/.test(r.cuerpo)).map((r) => r.selector);
    expect(sinColumna).toEqual([]);
  });
});
