import { describe, expect, test } from "vitest";

// Como src/comun/ZonaDeSoltar.test.ts: con `css: false` el `?raw` de un .scss llega vacio; se lee con el modulo de Node.
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const fuente = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/paginas/reajuste/reajuste.scss`, "utf-8");

// Ronda 1 del arbitro, punto 4: el titulo del resultado y la zona del aviso reciben el foco tras «Calcular» (VB-13);
// su anillo es el de Carbon (token `--cds-focus`, 2 px), no el del navegador. jsdom no calcula CSS: se lee el fuente.
describe("Reajuste: anillo de foco de Carbon en lo que recibe el foco tras calcular", () => {
  test("una regla :focus con outline de 2 px en var(--cds-focus) para el titulo y la zona del aviso", () => {
    const i = fuente.indexOf(".silice-reajuste__enfocable:focus");
    expect(i).toBeGreaterThanOrEqual(0);
    const regla = fuente.slice(i, fuente.indexOf("}", i));
    expect(regla).toMatch(/outline:\s*2px solid var\(--cds-focus\)/);
  });

  // VD-11: la celda de la papelera no hereda el minimo de 9rem de las celdas de campo (a 1056 px la tabla
  // «Períodos» desbordaba su contenedor 49 px). La medida que da fe es la del navegador (informe de VD-11).
  test("la columna de la papelera anula el minimo de ancho de las celdas de campo", () => {
    const i = fuente.indexOf(".silice-filas__quitar");
    expect(i).toBeGreaterThanOrEqual(0);
    const regla = fuente.slice(i, fuente.indexOf("}", i));
    expect(regla).toMatch(/min-inline-size:\s*0/);
  });

  // Ronda 2: la pagina (la ventana) se desplaza bajo la cabecera fija del marco (3rem = 48 px, `position: fixed`).
  // `scrollIntoView({ block: "start" })` dejaba el titulo enfocado en y=0, tapado (WCAG 2.4.11). El margen de
  // desplazamiento tiene que cubrir la cabecera mas el anillo (2 px de borde y 2 px de separacion): al menos 52 px.
  test("lo que recibe el foco se detiene bajo la cabecera fija con su anillo: scroll-margin-block-start >= 52 px", () => {
    const i = fuente.indexOf(".silice-reajuste__enfocable {");
    expect(i).toBeGreaterThanOrEqual(0);
    const regla = fuente.slice(i, fuente.indexOf("}", i));
    const valor = /scroll-margin-block-start:\s*([^;]+);/.exec(regla)?.[1] ?? "";
    // solo sumas de rem y px (16 px por rem)
    expect(valor).toMatch(/^(calc\()?[\d.]+(rem|px)(\s*\+\s*[\d.]+(rem|px))*\)?$/);
    const px = [...valor.matchAll(/([\d.]+)(rem|px)/g)].reduce((s, m) => s + Number(m[1]) * (m[2] === "rem" ? 16 : 1), 0);
    expect(px).toBeGreaterThanOrEqual(52);
  });
});
