import { green50, green60, gray10, gray70, red60, white } from "@carbon/colors";
import { describe, expect, test } from "vitest";

const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const leer = (ruta: string) => nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/${ruta}`, "utf-8");
const tokens = leer("src/estilos/tokens.scss");
const estilos = leer("src/indicadores/indicadores.scss");

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

// V-16: el libro menor que Silice sale en verde. El token de los iconos (--silice-verificado, green-50) da 3:1 sobre los
// fondos del tema (grafico, WCAG 1.4.11) pero NO 4.5:1 como texto de 12 px (1.4.3): el texto usa green-60.
describe("contraste de la variacion IBCS (V-16)", () => {
  test("el verde del icono llega a 3:1 sobre el fondo blanco y el gris 10 del tema", () => {
    expect(contraste(green50, white)).toBeGreaterThanOrEqual(3);
    expect(contraste(green50, gray10)).toBeGreaterThanOrEqual(3);
  });

  test.each([
    ["verde favorable", green60],
    ["rojo desfavorable", red60],
    ["gris sin variacion", gray70],
  ])("el texto %s llega a 4.5:1 sobre blanco y sobre el gris 10", (_n, color) => {
    expect(contraste(color, white)).toBeGreaterThanOrEqual(4.5);
    expect(contraste(color, gray10)).toBeGreaterThanOrEqual(4.5);
  });

  test("los tokens son colores de Carbon, no hexadecimales a mano", () => {
    expect(tokens).toMatch(/--silice-ibcs-favorable-texto:\s*#\{colors\.\$green-60\}/);
    expect(tokens).toMatch(/--silice-verificado:\s*#\{colors\.\$green-50\}/);
  });

  test("el texto favorable usa el token de texto y su icono el token del sistema --silice-verificado", () => {
    expect(estilos).toMatch(/\.ibcs-favorable\s*\{[^}]*color:\s*var\(--silice-ibcs-favorable-texto\)/);
    expect(estilos).toMatch(/\.ibcs-favorable\s*\{[^}]*svg\s*\{[^}]*fill:\s*var\(--silice-verificado\)/);
  });
});
