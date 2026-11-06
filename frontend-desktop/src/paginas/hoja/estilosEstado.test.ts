import { describe, expect, test } from "vitest";

// D13 de la tanda de detalles: a 1366 px la columna «Estado» del Presupuesto (penúltima de 10) quedaba cortada en el borde
// de la región que se desplaza (árbitro final de F6, `hoja.scss`). jsdom no calcula el diseño: aquí solo se comprueba que
// las reglas estén escritas; el efecto (el Estado entero a 1366, sin romper la tabla a 1056 y 1920) se MIDE en navegador.
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }
).process;
const estilos = nodo
  .getBuiltinModule("node:fs")
  .readFileSync(`${nodo.cwd()}/src/paginas/hoja/hoja.scss`, "utf-8")
  .replace(/\/\*[\s\S]*?\*\//g, "")
  .replace(/\/\/.*$/gm, "");

// El cuerpo de la primera regla `selector { ... }` (sin anidados) que empieza con ese selector.
function regla(selector: string, texto = estilos): string {
  const i = texto.indexOf(`${selector} {`);
  expect(i, `falta la regla ${selector}`).toBeGreaterThanOrEqual(0);
  let hondo = 0;
  const desde = texto.indexOf("{", i);
  for (let k = desde; k < texto.length; k++) {
    if (texto[k] === "{") hondo++;
    if (texto[k] === "}" && --hondo === 0) return texto.slice(desde + 1, k);
  }
  throw new Error(`regla ${selector} sin cierre`);
}
const rem = (cuerpo: string, propiedad: string): number => {
  const m = new RegExp(propiedad + String.raw`:\s*([\d.]+)rem`).exec(cuerpo);
  expect(m, `falta ${propiedad} en rem`).not.toBeNull();
  return Number(m![1]);
};

describe("columna Estado del Presupuesto a 1366 px (D13)", () => {
  test("el texto del Estado no pide más de 10 rem de ancho mínimo, para caber con las demás columnas a 1366 px", () => {
    expect(rem(regla(".silice-hoja__estado-texto"), "min-inline-size")).toBeLessThanOrEqual(10);
  });

  test("el Estado y su botón «Ver en Revisión» envuelven en vez de alargar la celda", () => {
    expect(regla(".silice-hoja__estado-fila")).toMatch(/flex-wrap:\s*wrap/);
  });

  test("el Estado se lee entero: hasta 4 líneas antes de recortar (el texto completo sigue en el title)", () => {
    expect(regla(".silice-hoja__estado-texto")).toMatch(/line-clamp:\s*4/);
  });
});
