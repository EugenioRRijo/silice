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
// derecho (su envoltorio cedía ancho y el botón desbordaba). F6, T6: la barra ya no lleva migas ni tamaño de letra; el
// espacio flexible lo ocupa la carpeta activa. Orden de cesión: primero el buscador (hasta su ícono), luego la carpeta
// activa, que se recorta con puntos suspensivos; la marca y la persona no ceden. La medida real se hace en el navegador;
// aquí se vigilan las reglas.
describe("la barra superior cabe en 1366 px con letra Normal", () => {
  const barra = () => leer("marco/BarraSuperior.scss");
  const regla = (selector: string) => reglaDe(barra(), selector) ?? `(no hay regla ${selector})`;
  const encoger = (texto: string) => Number(/flex:\s*[\d.]+\s+([\d.]+)/.exec(texto)?.[1] ?? "NaN");

  test("la marca y la persona no ceden ancho, y el tamaño de letra ya no tiene reglas en la barra", () => {
    expect(regla(".silice-marco-barra .silice-cuenta")).toMatch(/flex:\s*none/);
    expect(regla(".silice-marco-barra__marca")).toMatch(/flex:\s*none/);
    expect(barra()).not.toMatch(/silice-letra/);
  });

  test("el buscador cede antes que nada y, encogido, deja ver su ícono sin desbordar", () => {
    const buscar = regla(".silice-marco-barra__buscar");
    expect(encoger(buscar)).toBeGreaterThanOrEqual(100);
    expect(buscar).toMatch(/overflow:\s*hidden/);
    expect(buscar).toMatch(/min-inline-size:\s*2\.5rem/);
  });

  test("la carpeta activa ocupa el hueco flexible, cede después del buscador y se recorta con puntos suspensivos", () => {
    const carpeta = regla(".silice-marco-barra__carpeta");
    expect(carpeta).toMatch(/flex:\s*1\s+\d+\s+auto/);
    expect(carpeta).toMatch(/min-inline-size:\s*0/);
    expect(carpeta).toMatch(/overflow:\s*hidden/);
    expect(carpeta).toMatch(/text-overflow:\s*ellipsis/);
    expect(carpeta).toMatch(/white-space:\s*nowrap/);
    expect(encoger(regla(".silice-marco-barra__buscar"))).toBeGreaterThan(encoger(carpeta));
  });

  test("ya no hay reglas de migas", () => {
    expect(barra()).not.toMatch(/__migas|__miga-actual|__separador/);
  });

  test("el enlace de la persona marca la sección actual con el fondo y la raya del acento, no solo con color", () => {
    const actual = regla(".silice-marco-barra .silice-cuenta .silice-cuenta__boton[aria-current=\"page\"]");
    expect(actual).toMatch(/background-color:\s*var\(--cds-background-inverse-hover\)/);
    expect(actual).toMatch(/border-block-end:\s*2px solid var\(--silice-acento\)/);
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
