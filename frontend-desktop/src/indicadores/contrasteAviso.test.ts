import { gray10, white, yellow30, yellow50 } from "@carbon/colors";
import { describe, expect, test } from "vitest";

interface Fs {
  readdirSync(carpeta: string, o: { withFileTypes: true }): { name: string; isDirectory(): boolean }[];
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }
).process;
const fs = nodo.getBuiltinModule("node:fs");
const raiz = `${nodo.cwd()}/src`;
const leer = (ruta: string) => fs.readFileSync(`${raiz}/${ruta}`, "utf-8");
function archivos(carpeta: string, ext: RegExp): string[] {
  return fs.readdirSync(carpeta, { withFileTypes: true }).flatMap((e) => {
    const ruta = `${carpeta}/${e.name}`;
    return e.isDirectory() ? archivos(ruta, ext) : ext.test(e.name) ? [ruta] : [];
  });
}

function luminancia(hex: string): number {
  const canal = (i: number) => {
    const c = parseInt(hex.slice(1 + 2 * i, 3 + 2 * i), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * canal(0) + 0.7152 * canal(1) + 0.0722 * canal(2);
}
function contraste(a: string, b: string): number {
  const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

// Pasada en el navegador de F6 (H1): el ícono «Aviso» de la Bandeja de Pendientes y de «Lo que requiere atención» medía
// 1,53:1 sobre el gris 10 del tema (rgb 244,244,244). WCAG 1.4.11 pide 3:1 a un gráfico. El amarillo 30 de la severidad
// sigue siendo el de los halos de la hoja (lleva su contorno oscuro; `visor.scss`); el ícono usa su propio token, el
// ámbar 50 que ya da 3:1 a la franja de la etiqueta del libro menor. La urgencia se dice además con la palabra «Aviso».
describe("contraste del ícono de advertencia (H1)", () => {
  const tokens = leer("estilos/tokens.scss");

  test("el amarillo 30 de los halos no llega a 3:1 sobre el gris 10: por eso el ícono no lo usa", () => {
    expect(contraste(yellow30, gray10)).toBeCloseTo(1.53, 2);
    expect(contraste(yellow30, white)).toBeLessThan(3);
  });

  test("el ámbar 50 del ícono llega a 3:1 sobre el gris 10 del tema (3,03:1) y sobre el blanco (3,34:1)", () => {
    expect(contraste(yellow50, gray10)).toBeCloseTo(3.03, 2);
    expect(contraste(yellow50, gray10)).toBeGreaterThanOrEqual(3);
    expect(contraste(yellow50, white)).toBeCloseTo(3.34, 2);
    expect(contraste(yellow50, white)).toBeGreaterThanOrEqual(3);
  });

  test("el token del ícono es el ámbar 50 de Carbon, y el de los halos sigue siendo el amarillo 30", () => {
    expect(tokens).toMatch(/--silice-sev-advertencia-icono:\s*#\{colors\.\$yellow-50\}/);
    expect(tokens).toMatch(/--silice-sev-advertencia:\s*#\{colors\.\$yellow-30\}/);
  });

  test("el ícono de severidad «advertencia» (Bandeja, Vista general, hallazgos) pinta con el token del ícono", () => {
    const estilos = leer("indicadores/indicadores.scss");
    expect(estilos).toMatch(/\.silice-sev--advertencia\s+\.silice-sev__icono\s*\{[^}]*color:\s*var\(--silice-sev-advertencia-icono\)/);
  });

  test("ningún .scss propio pinta un ícono (fill o color) con el amarillo de los halos", () => {
    const malos = archivos(raiz, /\.scss$/)
      .filter((f) => /(?:^|[^-\w])(?:fill|color):\s*var\(--silice-sev-advertencia\)/m.test(fs.readFileSync(f, "utf-8")))
      .map((f) => f.slice(raiz.length));
    expect(malos).toEqual([]);
  });

  test("el ícono de advertencia de la arenera usa el token del ícono", () => {
    expect(leer("paginas/inicio/inicio.scss")).toMatch(/\.silice-inicio__icono--advertencia\s*\{[^}]*fill:\s*var\(--silice-sev-advertencia-icono\)/);
  });

  // El atípico (RF-100) pone el color de la advertencia en morado por esta variable: el ícono lee la suya, así que quien
  // la cambia debe cambiar las dos o el atípico volvería a salir ámbar.
  test.each(["paginas/hoja/PestanaPrecios.tsx", "paginas/precios_empresa/index.tsx"])("%s: el morado del atípico cubre también el ícono", (archivo) => {
    expect(leer(archivo)).toMatch(/MORADO_ATIPICO\s*=\s*\{[^}]*"--silice-sev-advertencia-icono":\s*"var\(--silice-atipico\)"/);
  });
});
