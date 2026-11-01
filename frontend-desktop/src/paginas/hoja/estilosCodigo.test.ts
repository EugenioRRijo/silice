import { describe, expect, test } from "vitest";

const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const scss = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/paginas/hoja/hoja.scss`, "utf-8");

describe("el código de partida de la Hoja", () => {
  test("no se parte en líneas", () => {
    expect(scss).toMatch(/\.silice-hoja__codigo\s*\{[^}]*white-space:\s*nowrap/);
  });
});
