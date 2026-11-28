// Vigila lo que jsdom no dibuja (como visor/visor.estilos.test.ts): compila el SCSS real y lee las reglas.
import * as sass from "sass";
import { describe, expect, test } from "vitest";

const nodo = (globalThis as unknown as { process: { cwd(): string } }).process;
const css = sass.compile(`${nodo.cwd()}/src/paginas/administracion/administracion.scss`).css;

function regla(selector: string): string {
  const escapado = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const m = new RegExp(`(?:^|\\})\\s*${escapado}\\s*\\{([^}]*)\\}`, "m").exec(css);
  if (!m) throw new Error(`No hay una regla para ${selector}`);
  return m[1];
}

// Revisión visual de la Cuenta (T3, 2026-11-28, 1366 px): en Solicitudes la tabla partía «Pendiente» en «Pendient / e», la fecha
// en «28/11/202 / 6» y el usuario en «persona.fict / icia». Con `overflow-wrap: anywhere` el ancho mínimo de una celda es el de una
// sola letra, así que el navegador repartía el ancho a favor de la columna de botones. Con `break-word` el mínimo es la palabra
// más larga (la tabla ya desplaza dentro de su caja si hace falta) y una cadena sin espacios sigue sin romper la página.
describe("las tablas de la Cuenta no parten las palabras cortas", () => {
  test("las celdas rompen una palabra solo si no cabe en la caja, sin bajar el ancho mínimo de la columna", () => {
    const celdas = regla(".silice-adm__tabla td");
    expect(celdas).toMatch(/overflow-wrap:\s*break-word/);
    expect(celdas).not.toMatch(/anywhere/);
  });
});
