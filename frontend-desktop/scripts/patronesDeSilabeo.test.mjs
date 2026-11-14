// F8, C4: Univer trae los patrones de silabeo de 70 idiomas como trozos perezosos (unos 4,4 MB del dist). Sílice solo
// los usaría con el silabeo automático de un documento, que la hoja no activa; se conservan el español y el inglés.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";
import { IDIOMAS_CONSERVADOS, esCargadorDePatrones, podarPatrones } from "./patronesDeSilabeo.mjs";

// Un trozo con la forma exacta del código generado de `@univerjs/engine-render` 1.0.3 (pattern-loaders.gen.ts).
const MUESTRA = [
  "//#region src/components/docs/layout/hyphenation/pattern-loaders.gen.ts",
  "const PATTERN_LOADERS = {",
  '\t["af"]: () => import("./af-DK_CjRn6.js"),',
  '\t["de-1901"]: () => import("./de-1901-CWoAOigE.js"),',
  '\t["en-gb"]: () => import("./en-gb-B7Al27b_.js"),',
  '\t["en-us"]: () => Promise.resolve().then(() => en_us_exports),',
  '\t["es"]: () => import("./es-DcaaHPU_.js"),',
  '\t["zh-latn-pinyin"]: () => import("./zh-latn-pinyin-BdYb-Ey_.js")',
  "};",
  "const otra = { a: () => import(\"./af-DK_CjRn6.js\") };",
].join("\n");

describe("podarPatrones", () => {
  test("conserva solo el español y el inglés y deja el resto del archivo como estaba", () => {
    const podado = podarPatrones(MUESTRA);
    expect(podado).toContain('["es"]: () => import("./es-DcaaHPU_.js")');
    expect(podado).toContain('["en-gb"]: () => import("./en-gb-B7Al27b_.js")');
    expect(podado).toContain('["en-us"]: () => Promise.resolve().then(() => en_us_exports)');
    expect(podado).not.toContain('["af"]');
    expect(podado).not.toContain('["de-1901"]');
    expect(podado).not.toContain("zh-latn-pinyin");
    // Fuera de la tabla no se toca nada.
    expect(podado).toContain('const otra = { a: () => import("./af-DK_CjRn6.js") };');
    expect(podado.startsWith("//#region src/components/docs/layout/hyphenation/pattern-loaders.gen.ts\nconst PATTERN_LOADERS = {")).toBe(true);
  });

  test("lo podado sigue siendo un objeto de JavaScript válido con las claves conservadas", () => {
    const tabla = podarPatrones(MUESTRA).split("const PATTERN_LOADERS = ")[1].split("\nconst otra")[0];
    const objeto = new Function("en_us_exports", `return ${tabla.replace(/;\s*$/, "")}`)({});
    expect(Object.keys(objeto).sort()).toEqual(["en-gb", "en-us", "es"]);
  });

  test("sin la tabla (otra versión de Univer) falla en voz alta en vez de no hacer nada", () => {
    expect(() => podarPatrones("const OTRA = {};")).toThrow(/PATTERN_LOADERS/);
  });

  test("los idiomas conservados son el español y los dos ingleses", () => {
    expect([...IDIOMAS_CONSERVADOS].sort()).toEqual(["en-gb", "en-us", "es"]);
  });

  test("solo se aplica al índice de engine-render", () => {
    expect(esCargadorDePatrones("C:/x/node_modules/@univerjs/engine-render/lib/es/index.js")).toBe(true);
    expect(esCargadorDePatrones("/x/node_modules/@univerjs/engine-render/lib/es/index.js?v=1")).toBe(true);
    expect(esCargadorDePatrones("/x/node_modules/@univerjs/engine-render/lib/es/es-DcaaHPU_.js")).toBe(false);
    expect(esCargadorDePatrones("/x/node_modules/@univerjs/core/lib/es/index.js")).toBe(false);
    expect(esCargadorDePatrones("/x/src/index.js")).toBe(false);
  });

  test("con la versión instalada de Univer la tabla se encuentra y se poda", () => {
    const raiz = dirname(dirname(fileURLToPath(import.meta.url)));
    const indice = join(raiz, "node_modules", "@univerjs", "engine-render", "lib", "es", "index.js");
    const codigo = readFileSync(indice, "utf-8");
    const podado = podarPatrones(codigo);
    const importaciones = (texto) => (texto.split("const PATTERN_LOADERS = {")[1].split("};")[0].match(/import\(/g) ?? []).length;
    expect(importaciones(codigo)).toBeGreaterThan(60);
    expect(importaciones(podado)).toBe(2);
  });
});
