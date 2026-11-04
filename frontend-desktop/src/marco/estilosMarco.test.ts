import { describe, expect, test } from "vitest";

// jsdom no calcula CSS: las reglas se leen del fuente (como shell/AnilloDelTitulo.test.ts) y se midieron en el navegador.
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const leer = (ruta: string) => nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/${ruta}`, "utf-8");

function reglaDe(fuente: string, selector: string): string | null {
  const i = fuente.indexOf(`${selector} {`);
  if (i < 0) return null;
  const abre = fuente.indexOf("{", i);
  return fuente.slice(i, fuente.indexOf("}", abre));
}

// Pasada en el navegador del cierre de F2: el cuerpo reserva 3 rem arriba para una cabecera fija (la de Carbon de las
// pantallas sin marco, visor.scss); la barra del marco iba en el flujo y quedaba una franja vacía encima. La barra del
// marco también es fija, a lo ancho, y el marco ocupa el alto que queda debajo.
describe("la barra superior del marco ocupa el hueco que reserva el cuerpo", () => {
  test("el cuerpo reserva 3 rem para una cabecera fija", () => {
    expect(reglaDe(leer("visor/visor.scss"), "body")).toMatch(/padding-block-start:\s*3rem/);
  });

  test("la barra del marco es fija arriba, a lo ancho, y el marco mide el alto que queda", () => {
    const marco = leer("marco/marco.scss");
    const barra = reglaDe(marco, "  > .silice-marco-barra");
    expect(barra).toMatch(/position:\s*fixed/);
    expect(barra).toMatch(/inset-block-start:\s*0/);
    expect(barra).toMatch(/inset-inline:\s*0/);
    expect(reglaDe(marco, ".silice-marco")).toMatch(/min-block-size:\s*calc\(100vh - 3rem\)/);
  });
});

// Hallazgo 7 del recorrido (01-11-2026, 1366×768, letra Normal): en las pantallas de obra la cuenta se salía por el borde
// derecho (su envoltorio cedía ancho y el botón desbordaba) y la miga quedaba en «Mis ob… / Vía Ficticia El En… / Tra…».
// Orden de cesión: primero el buscador (hasta su ícono), luego las migas intermedias; la sección actual, la cuenta y el
// tamaño de letra no ceden. La medida real se hace en el navegador; aquí se vigilan las reglas.
describe("la barra superior cabe en 1366 px con letra Normal", () => {
  const barra = () => leer("marco/BarraSuperior.scss");
  const regla = (selector: string) => reglaDe(barra(), selector) ?? `(no hay regla ${selector})`;
  const encoger = (texto: string) => Number(/flex:\s*[\d.]+\s+([\d.]+)/.exec(texto)?.[1] ?? "NaN");

  test("la cuenta y el tamaño de letra no ceden ancho", () => {
    expect(regla(".silice-marco-barra .silice-cuenta")).toMatch(/flex:\s*none/);
    expect(regla(".silice-marco-barra .silice-letra")).toMatch(/flex:\s*none/);
  });

  test("el buscador cede antes que nada y, encogido, deja ver su ícono sin desbordar", () => {
    const buscar = regla(".silice-marco-barra__buscar");
    expect(encoger(buscar)).toBeGreaterThanOrEqual(100);
    expect(buscar).toMatch(/overflow:\s*hidden/);
    expect(buscar).toMatch(/min-inline-size:\s*2\.5rem/);
  });

  test("las migas intermedias ceden antes que la sección actual, que se lee entera", () => {
    const intermedias = regla(".silice-marco-barra__migas li");
    const actual = regla(".silice-marco-barra__migas li:last-child");
    expect(encoger(intermedias)).toBeGreaterThanOrEqual(100);
    expect(encoger(actual)).toBe(1);
    expect(encoger(intermedias)).toBeGreaterThan(encoger(actual));
    expect(encoger(regla(".silice-marco-barra__buscar"))).toBeGreaterThanOrEqual(encoger(intermedias));
    // Una intermedia recortada conserva unas letras («Mis…»), no desaparece.
    expect(intermedias).toMatch(/min-inline-size:\s*[1-9][\d.]*rem/);
  });

  test("sin colores nuevos: solo tokens", () => {
    expect(barra()).not.toMatch(/#[0-9a-fA-F]{3,8}\b|rgba?\(/);
  });
});

// Plan F6, T3: la barra de espacio parte en renglones con cualquier cantidad de pestañas y cualquier letra, así que no
// puede declarar un ancho fijo (ni en px ni en rem) en ella ni en sus pestañas.
describe("la barra de espacio no declara anchos fijos", () => {
  test("ni width ni inline-size (ni sus mínimos y máximos) con un valor fijo", () => {
    const fuente = leer("marco/BarraDeEspacio.scss");
    expect(fuente.match(/(?:^|[\s;{])(?:min-|max-)?(?:width|inline-size)\s*:\s*[\d.]+(?:px|rem|em)\b/g)).toBeNull();
    expect(fuente).toMatch(/flex-wrap:\s*wrap/);
  });
});
