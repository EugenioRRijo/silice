import { gray100, green50, green60, gray10, gray70, red60, white, yellow10, yellow50 } from "@carbon/colors";
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

// V-16 (etiqueta del libro menor): texto de 12 a 14 px sobre un fondo propio, con AA (4.5:1); la franja y el icono, 3:1 contra
// el fondo del indicador (blanco o gris 10) para que el verde no se lea como «todo bien» (forma, no solo color).
describe("contraste de la etiqueta del libro menor (V-16)", () => {
  test("el texto de la etiqueta llega a 4.5:1 sobre su fondo", () => {
    expect(contraste(gray100, yellow10)).toBeGreaterThanOrEqual(4.5);
  });

  test("la franja y el icono llegan a 3:1 sobre el fondo de la etiqueta y sobre los fondos del indicador", () => {
    for (const fondo of [yellow10, white, gray10]) expect(contraste(yellow50, fondo)).toBeGreaterThanOrEqual(3);
  });

  test("los tokens son colores de Carbon, no hexadecimales a mano", () => {
    expect(tokens).toMatch(/--silice-aviso-fondo:\s*#\{colors\.\$yellow-10\}/);
    expect(tokens).toMatch(/--silice-aviso-borde:\s*#\{colors\.\$yellow-50\}/);
  });

  test("los estilos usan los tokens, texto en la tinta normal, sin hexadecimales y con franja y borde", () => {
    const regla = estilos.match(/\.fiori-kpi__aviso\s*\{[^}]*\}/)?.[0] ?? "";
    expect(regla).toMatch(/background:\s*var\(--silice-aviso-fondo\)/);
    expect(regla).toMatch(/border-inline-start:\s*4px solid var\(--silice-aviso-borde\)/);
    expect(regla).toMatch(/color:\s*var\(--silice-texto\)/);
    expect(regla).not.toMatch(/#[0-9a-fA-F]{3,8}\b/);
  });

  test("el texto se ve completo: ni elipsis ni recorte, y baja de linea", () => {
    const regla = estilos.match(/\.fiori-kpi__aviso\s*\{[^}]*\}/)?.[0] ?? "";
    expect(regla).not.toMatch(/overflow:\s*hidden|text-overflow|nowrap/);
  });

  test("al imprimir, los colores se conservan (la etiqueta sale en el papel); con colores forzados lleva borde propio", () => {
    expect(estilos).toMatch(/\.fiori-kpi__aviso\s*\{[^}]*print-color-adjust:\s*exact/);
    expect(estilos).toMatch(/@media \(forced-colors: active\)\s*\{[^}]*\.fiori-kpi__aviso/);
  });

  test("la franja crece solo lo que pide la etiqueta: alto minimo de 4rem, no fijo", () => {
    expect(estilos).toMatch(/\.franja-indicadores\s*\{[^}]*min-block-size:\s*4rem/);
    expect(estilos).not.toMatch(/\.franja-indicadores\s*\{[^}]*[^-]block-size:\s*4rem/);
  });
});
