import { describe, expect, test } from "vitest";

// jsdom no calcula CSS: la regla se lee del fuente (como en comun/AnilloDeFoco.test.ts) y el anillo se midio en el navegador.
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const fuente = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/shell/shell.scss`, "utf-8");

function reglaDe(selector: string): string | null {
  const i = fuente.indexOf(selector);
  if (i < 0) return null;
  const abre = fuente.indexOf("{", i);
  return fuente.slice(i, fuente.indexOf("}", abre));
}

// VD-7, ronda 2 del arbitro: en «Libro de la empresa» el h1 enfocado tiene relleno propio y su caja empieza pegada a la
// cabecera fija, al menu y a la banda de indicadores: un anillo hacia afuera quedaba tapado por los tres. Alli va hacia
// adentro; en las demas paginas (h1 sin relleno, 24 px bajo la cabecera) va hacia afuera y no toca la primera letra.
describe("anillo del h1 que recibe el foco al cambiar de pagina", () => {
  const general = reglaDe('h1[tabindex="-1"]:focus-visible');
  const libro = reglaDe('.silice-pagina-libro > h1[tabindex="-1"]:focus-visible');

  test("en general: 2 px con el token de foco y separado 2 px hacia afuera", () => {
    expect(general).not.toBeNull();
    expect(general).toMatch(/outline:\s*2px solid var\(--cds-focus\)/);
    expect(general).toMatch(/outline-offset:\s*2px/);
  });

  test("en el Libro: el mismo anillo pero hacia adentro (offset -2px), para que no lo tapen cabecera, menu ni banda", () => {
    expect(libro).not.toBeNull();
    expect(libro).toMatch(/outline:\s*2px solid var\(--cds-focus\)/);
    expect(libro).toMatch(/outline-offset:\s*-2px/);
  });

  test("sin colores sueltos ni sombras", () => {
    for (const r of [general, libro]) expect(r).not.toMatch(/#[0-9a-fA-F]{3,8}\b|rgb\(|box-shadow/);
  });
});
