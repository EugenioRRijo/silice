import { describe, expect, test } from "vitest";

const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const estilos = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/indicadores/indicadores.scss`, "utf-8");
// Lo que declaran, juntas, todas las reglas cuya lista de selectores nombra a `selector` (una puede ir compartida con otra).
const sinComentarios = estilos.replace(/^\s*\/\/.*$/gm, "");
function regla(selector: string): string {
  const cuerpos: string[] = [];
  for (const m of sinComentarios.matchAll(/([^{}]+)\{([^}]*)\}/g)) {
    if (m[1].split(",").some((s) => s.trim() === selector)) cuerpos.push(m[2]);
  }
  return cuerpos.join(";");
}

// Pasada en el navegador de F6 (H4): la barra de avance medía 6 px en letra Normal y en Muy grande (3 px de relleno y un
// contorno de 1 px), mientras la cifra de encima pasaba de 21 a 63 px de alto. Los altos van en rem, que crecen con la
// letra (`--silice-escala-letra` en la raíz). IBCS no cambia: el real, relleno sólido; el plan, contorno.
describe("la barra de avance crece con la letra (H4)", () => {
  test.each([".fiori-kpi__barra", ".fiori-kpi__barra-real", ".fiori-kpi__barra-meta"])("%s da su alto en rem, no en px", (selector) => {
    expect(regla(selector)).toMatch(/block-size:\s*[\d.]+rem/);
    expect(regla(selector)).not.toMatch(/block-size:\s*[\d.]+px/);
  });

  test("el contorno del plan no es más fino que el del contorno de 1 px de antes", () => {
    expect(regla(".fiori-kpi__barra-meta")).toMatch(/border:\s*(?:[\d.]+rem|1px)\s+solid/);
  });

  test("IBCS: el real es un relleno sólido y el plan un contorno sin relleno", () => {
    expect(regla(".fiori-kpi__barra-real")).toMatch(/background:\s*var\(--silice-texto\)/);
    expect(regla(".fiori-kpi__barra-meta")).toMatch(/background:\s*transparent/);
    expect(regla(".fiori-kpi__barra-meta")).toMatch(/border:[^;]*var\(--silice-texto\)/);
  });

  test("el real y el plan caben dentro de la barra: el alto de la barra no es menor que lo que apilan", () => {
    const rem = (texto: string, propiedad: string) => Number(new RegExp(`(?:^|[\\s;])${propiedad}:\\s*([\\d.]+)rem`).exec(texto)?.[1] ?? NaN);
    const barra = rem(regla(".fiori-kpi__barra"), "block-size");
    const real = rem(regla(".fiori-kpi__barra-real"), "block-size");
    const meta = rem(regla(".fiori-kpi__barra-meta"), "block-size");
    const arriba = rem(regla(".fiori-kpi__barra-meta"), "inset-block-start");
    expect(barra).toBeGreaterThanOrEqual(0.5);
    expect(arriba + meta).toBeLessThanOrEqual(barra);
    expect(real).toBeLessThanOrEqual(arriba);
  });
});
