import { describe, expect, test } from "vitest";

interface Fs {
  readdirSync(carpeta: string, o: { withFileTypes: true }): { name: string; isDirectory(): boolean }[];
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }
).process;
const fs = nodo.getBuiltinModule("node:fs");

function archivos(carpeta: string, ext: RegExp): string[] {
  return fs.readdirSync(carpeta, { withFileTypes: true }).flatMap((e) => {
    const ruta = `${carpeta}/${e.name}`;
    return e.isDirectory() ? archivos(ruta, ext) : ext.test(e.name) && !/\.test\./.test(e.name) ? [ruta] : [];
  });
}
const raiz = `${nodo.cwd()}/src`;
const leer = (ruta: string) => fs.readFileSync(ruta, "utf-8");

// Letra grande por presbicia: todo el texto sale del tamaño de la raíz (rem). Un `font-size` en píxeles o una `fontSize`
// numérica en el código no crecería con el control «Tamaño de letra» y volvería a dejar texto pequeño.
describe("tamaño de letra en el CSS propio", () => {
  test("ningún .scss propio fija font-size en px ni en pt", () => {
    const malos = archivos(raiz, /\.scss$/)
      .filter((f) => /font-size:\s*[\d.]+(px|pt)/.test(leer(f)))
      .map((f) => f.slice(raiz.length));
    expect(malos).toEqual([]);
  });

  test("ningún componente fija fontSize en px o con un número (React lo toma como px)", () => {
    const malos = archivos(raiz, /\.tsx?$/)
      .filter((f) => /fontSize:\s*(\d|["'`][\d.]+px)/.test(leer(f)))
      .map((f) => f.slice(raiz.length));
    expect(malos).toEqual([]);
  });

  test("el CSS no usa el abreviado «font:» con píxeles", () => {
    const malos = archivos(raiz, /\.scss$/)
      .filter((f) => /[^-]font:\s*[^;]*\d+px/.test(leer(f)))
      .map((f) => f.slice(raiz.length));
    expect(malos).toEqual([]);
  });

  test("la raíz toma el tamaño base (cuerpo de 16 px o más) por la variable del control", () => {
    const app = leer(`${raiz}/estilos/app.scss`);
    expect(app).toMatch(/html\s*\{[^}]*font-size:\s*calc\(\s*116\.6667%\s*\*\s*var\(--silice-escala-letra\)\s*\)/);
    const tokens = leer(`${raiz}/estilos/tokens.scss`);
    expect(tokens).toMatch(/--silice-escala-letra:\s*1;/);
  });

  test("con el tamaño base, el cuerpo de Carbon (14 px) llega a 16 px y la etiqueta más pequeña (12 px) a 14 px", () => {
    const base = 16 * 1.166667;
    expect(0.875 * base).toBeGreaterThanOrEqual(16);
    expect(0.75 * base).toBeGreaterThanOrEqual(14);
  });

  test("la barra pasa a capa antes con la letra grande (Grande bajo 1536 px, Muy grande bajo 1920 px) y cede el nombre", () => {
    const shell = leer(`${raiz}/shell/shell.scss`);
    const umbrales = leer(`${raiz}/shell/_umbrales.scss`);
    // Los umbrales viven solo en _umbrales.scss; shell.scss aplica el mixin por escala, sin cifras propias.
    expect(umbrales).toMatch(/"normal":\s*1055\.98px/);
    expect(umbrales).toMatch(/"grande":\s*1535\.98px/);
    expect(umbrales).toMatch(/"muy-grande":\s*1919\.98px/);
    for (const escala of ["normal", "grande", "muy-grande"]) {
      expect(shell).toContain(`@include menu-en-capa("${escala}");`);
    }
    expect(shell).toMatch(/@include u\.por-debajo-del-umbral\(\$escala\)/);
    // Ninguna consulta de medios en px (ni max- ni min-width): esas cifras son de _umbrales.scss.
    expect(shell).not.toMatch(/@media[^{]*\d+(\.\d+)?px/);
    // Por debajo del umbral la capa es la unica navegacion: sus areas (HeaderSideNavItems, ul.cds--side-nav__header-navigation)
    // deben verse aunque Carbon solo las muestre con su consulta en rem (<= 65.98rem), que no sigue la letra de Silice.
    const mixin = shell.slice(shell.indexOf("@mixin menu-en-capa"), shell.indexOf('@include menu-en-capa("normal")'));
    expect(mixin).toMatch(/\.cds--side-nav__header-navigation\s*\{[^}]*display:\s*block/);
    // La cuenta cede el nombre (queda en su nombre accesible) con letra Grande o Muy grande.
    const cuenta = leer(`${raiz}/shell/MenuCuenta.scss`);
    expect(cuenta).toMatch(/data-silice-letra="grande"\][^{]*data-silice-letra="muy-grande"\][^{]*\{\s*\.silice-cuenta__nombre\s*\{\s*display:\s*none/);
  });
});
