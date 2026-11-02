import { fileURLToPath } from "node:url";
import * as sass from "sass";
import { describe, expect, test } from "vitest";

// Prueba en vivo 2026-10-25 (capturas 08 y 11): en las tablas de insumos los encabezados de cifras van a la derecha
// (`silice-cifra`) pero el campo de texto de la celda escribia a la izquierda, y el relleno de la celda de Carbon
// (1 rem a cada lado) dejaba franjas grises entre campos y corria el texto del campo 1 rem respecto de su encabezado.
// jsdom no dibuja: se compila el SCSS real y se leen las reglas; el efecto se midio en el navegador.
// La ruta va en una variable, como en `visor.estilos.test.ts`: con el literal, Vite reescribe el `new URL` como recurso.
const compilar = (ruta: string) => sass.compile(fileURLToPath(new URL(ruta, import.meta.url))).css;
const css = compilar("./componer.scss");

function regla(selector: string): string {
  const escapado = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const m = new RegExp(`(?:^|\\})\\s*${escapado}\\s*\\{([^}]*)\\}`, "m").exec(css);
  if (!m) throw new Error(`No hay una regla para ${selector}`);
  return m[1];
}

describe("estilos de las tablas de insumos de Componer", () => {
  test("la celda no tiene relleno lateral: el texto del campo cae bajo el de su encabezado", () => {
    expect(regla(".silice-componer__tabla td")).toMatch(/padding-inline:\s*0/);
  });

  test("las cifras se escriben a la derecha, como su encabezado", () => {
    expect(regla(".silice-componer__tabla td.silice-cifra input")).toMatch(/text-align:\s*end/);
  });

  test("la descripción tiene más ancho que cada cifra y la columna de Borrar se ajusta a su botón", () => {
    expect(regla(".silice-componer__tabla th:first-child")).toMatch(/inline-size:\s*\d+%/);
    expect(regla(".silice-componer__tabla th:last-child")).toMatch(/inline-size:\s*1%/);
  });
});
