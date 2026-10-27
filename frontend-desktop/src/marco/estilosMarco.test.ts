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
