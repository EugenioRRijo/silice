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

  // Plan de modulos (MOD-2): el umbral en que la barra no cabe es por modulo y por letra, y por debajo sus areas pasan al
  // sidebar de modulos (no a una capa aparte). Las cifras viven solo en _umbrales.scss.
  test("la barra de cada módulo cede sus áreas al sidebar por debajo de su umbral, por letra, y la cuenta cede el nombre", () => {
    const shell = leer(`${raiz}/shell/shell.scss`);
    const umbrales = leer(`${raiz}/shell/_umbrales.scss`);
    // Medidos por el recorrido visual (MOD-5, `recorrido_ux_playwright.py --umbrales`; bitacora 2026-10-26-modulos.md
    // §6, ronda 2: sin holgura en los textos con puntos suspensivos y con la cuenta de nombre largo): el menor ancho en que la barra cabe con la obra de nombre mas largo de la siembra, menos 0,02 px, y nunca
    // por debajo de 1055,98 px (Carbon esconde la navegacion de la cabecera por debajo de 1056 px). Escritos a mano.
    const mapa = umbrales.slice(umbrales.indexOf("$umbrales-por-modulo"));
    expect(mapa).toMatch(/"auditoria":\s*\(\s*"normal":\s*1055\.98px,\s*"grande":\s*1135\.98px,\s*"muy-grande":\s*1340\.98px/);
    expect(mapa).toMatch(/"obras":\s*\(\s*"normal":\s*1909\.98px,\s*"grande":\s*1654\.98px,\s*"muy-grande":\s*1942\.98px/);
    expect(mapa).toMatch(/"produccion":\s*\(\s*"normal":\s*1055\.98px,\s*"grande":\s*1063\.98px,\s*"muy-grande":\s*1254\.98px/);
    // El fijado del sidebar: desde 1366 px con Normal y 1366 x 1,25 y x 1,5 con Grande y Muy grande.
    expect(umbrales).toMatch(/\$fijado-desde:\s*\(\s*"normal":\s*1366px,\s*"grande":\s*1708px,\s*"muy-grande":\s*2049px/);
    // La columna del recorrido sigue pasando a franja con los umbrales por letra de siempre.
    expect(umbrales).toMatch(/"normal":\s*1055\.98px/);
    expect(umbrales).toMatch(/"grande":\s*1535\.98px/);
    expect(umbrales).toMatch(/"muy-grande":\s*1919\.98px/);
    // shell.scss aplica el mixin a cada modulo y cada letra, sin cifras propias.
    expect(shell).toMatch(/@include u\.barra-no-cabe\(\$modulo, \$escala\)/);
    expect(shell).toMatch(/@include u\.fijado-posible/);
    expect(shell).not.toMatch(/@media[^{]*\d+(\.\d+)?px/);
    expect(shell).not.toContain("menu-en-capa");
    // Por debajo del umbral la barra esconde sus areas y el sidebar las muestra.
    const regla = shell.slice(shell.indexOf("@include u.barra-no-cabe"));
    expect(regla).toMatch(/\.silice-barra__nav\s*\{\s*display:\s*none/);
    expect(regla).toMatch(/\.silice-sidebar__areas\s*\{\s*display:\s*block/);
    // La cuenta cede el nombre (queda en su nombre accesible) con letra Grande o Muy grande.
    const cuenta = leer(`${raiz}/shell/MenuCuenta.scss`);
    expect(cuenta).toMatch(/data-silice-letra="grande"\][^{]*data-silice-letra="muy-grande"\][^{]*\{\s*\.silice-cuenta__nombre\s*\{\s*display:\s*none/);
  });
});
