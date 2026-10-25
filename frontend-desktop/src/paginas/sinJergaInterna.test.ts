import { describe, expect, test } from "vitest";

// Prueba en vivo 2026-10-25: Componer mostraba «(UC-07, flujo 3a)». Los codigos del expediente (casos de uso,
// requisitos, secciones de la especificacion) son de quien construye Silice, no de quien lo usa: en las paginas solo
// pueden ir en comentarios. jsdom no recorre todas las pantallas en todos sus estados: se lee el fuente, sin
// comentarios. Los textos que llegan de la API los vigila `tests/unit/test_aplicacion_composicion.py`.
interface Fs {
  readdirSync(carpeta: string, opciones: { recursive: true }): string[];
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }).process;
const fs = nodo.getBuiltinModule("node:fs");
const carpeta = `${nodo.cwd()}/src/paginas`;

const JERGA = /\b(?:UC|RF|RNF)[-‑]\d|spec\s*§/;

function sinComentarios(fuente: string): string {
  return fuente
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .split(/\r?\n/)
    .map((linea) => linea.replace(/(^|[^:"'`])\/\/.*$/, "$1"))
    .join("\n");
}

const fuentes = fs
  .readdirSync(carpeta, { recursive: true })
  .map((r) => r.replaceAll("\\", "/"))
  .filter((r) => /\.tsx?$/.test(r) && !/\.test\.tsx?$/.test(r));

describe("sin jerga interna en las paginas", () => {
  test("el filtro de comentarios deja las cadenas y quita los comentarios", () => {
    expect(sinComentarios('// UC-10 comentario\nconst t = "Texto RF-33";')).toBe('\nconst t = "Texto RF-33";');
    expect(sinComentarios("{/* RNF-08 */}<p>Hola</p>")).toBe("{}<p>Hola</p>");
    expect(JERGA.test(sinComentarios('const t = "Partida nueva (UC-07, flujo 3a)";'))).toBe(true);
  });

  test("ninguna pagina tiene un codigo UC-, RF-, RNF- ni «spec §» fuera de un comentario", () => {
    expect(fuentes.length).toBeGreaterThan(50); // la guardia no recorre una lista vacia
    const conJerga = fuentes.filter((r) => JERGA.test(sinComentarios(fs.readFileSync(`${carpeta}/${r}`, "utf-8"))));
    expect(conJerga).toEqual([]);
  });
});
