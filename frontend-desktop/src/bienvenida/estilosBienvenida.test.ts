import { describe, expect, test } from "vitest";

// Con `css: false` el `?raw` de un .scss llega vacío: se lee con el módulo de Node (como estilosPlano.test.ts).
interface Fs {
  readdirSync(carpeta: string): string[];
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs };
  }
).process;
const fs = nodo.getBuiltinModule("node:fs");
const carpeta = `${nodo.cwd()}/src/bienvenida`;
const estilos = fs.readFileSync(`${carpeta}/bienvenida.scss`, "utf-8");
const fuentes = fs
  .readdirSync(carpeta)
  .filter((n) => /\.tsx?$/.test(n) && !/\.test\.tsx?$/.test(n))
  .map((n) => ({ n, texto: fs.readFileSync(`${carpeta}/${n}`, "utf-8") }));

// jsdom no calcula el diseño: aquí solo se comprueba que las reglas estén escritas; el efecto se MIDE en navegador (F16, BCP-10).
describe("estilos de la bienvenida (F16, parte de BCP-4)", () => {
  test("ningún tamaño de texto ni de caja está en px: todo en rem (solo filetes y anillos de foco, que no escalan)", () => {
    const sinComentarios = estilos.replace(/\/\/.*$/gm, "").replace(/\/\*[\s\S]*?\*\//g, "");
    const conPx = sinComentarios.split("\n").filter((linea) => /\d\s*px\b/.test(linea));
    expect(conPx.length).toBeGreaterThan(0); // la regla se aplica: hay filetes y anillos en px
    for (const linea of conPx) expect(linea).toMatch(/^\s*(?:border[\w-]*|outline[\w-]*):/);
  });

  test("las columnas y los textos largos no desbordan: min-inline-size 0 y overflow-wrap anywhere", () => {
    expect(estilos).toMatch(/min-inline-size:\s*0/);
    expect(estilos).toMatch(/overflow-wrap:\s*anywhere/);
  });

  test("los campos pasan de dos columnas a una con auto-fit y minmax(min(100%, …))", () => {
    expect(estilos).toMatch(/repeat\(\s*auto-fit\s*,\s*minmax\(\s*min\(\s*100%\s*,\s*[\d.]+rem\s*\)\s*,\s*1fr\s*\)\s*\)/);
  });

  test("no hay alto fijo en las secciones ni animación decorativa", () => {
    expect(estilos).not.toMatch(/(?:^|[^-])(?:block-size|height):\s*[\d.]+(?:rem|vh|%)\s*;/m);
    expect(estilos).not.toMatch(/animation:|@keyframes|transition:/);
  });

  test("el resumen de errores enfocado por programa lleva anillo de foco visible", () => {
    expect(estilos).toMatch(/&:focus\s*\{[^}]*outline:\s*2px solid/);
  });
});

describe("la interfaz no calcula (F18) y los formularios usan CampoTexto (VB-18)", () => {
  test("ningún archivo de la carpeta usa Number(, parseFloat ni toFixed", () => {
    for (const { n, texto } of fuentes) {
      const sinComentarios = texto.replace(/\/\/.*$/gm, "");
      expect(sinComentarios, n).not.toMatch(/\bNumber\(|parseFloat|toFixed/);
    }
  });

  test("no importan TextInput de Carbon ni el Modal: campos con CampoTexto, sin diálogos de Carbon", () => {
    for (const { n, texto } of fuentes) {
      expect(texto, n).not.toMatch(/\bTextInput\b|\bComposedModal\b|\bModal\b/);
    }
  });

  test("el código y la contraseña no se escriben en el almacenamiento del navegador", () => {
    for (const { n, texto } of fuentes) {
      expect(texto, n).not.toMatch(/localStorage|sessionStorage/);
    }
  });
});
