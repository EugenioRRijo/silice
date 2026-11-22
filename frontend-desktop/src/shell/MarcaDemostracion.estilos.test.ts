import { describe, expect, test } from "vitest";

// jsdom no calcula CSS: la regla se lee del fuente (como marco/estilosMarco.test.ts).
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const leer = (ruta: string) => nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/${ruta}`, "utf-8");

// Eugenio, 2026-11-22 (captura): en la barra oscura, al pasar el cursor o con el foco, Carbon
// (`.cds--header__action:hover`, misma especificidad y cargado después) le ponía al botón «Demostración» el fondo
// oscuro de la barra y el texto oscuro quedaba ilegible. En todos los estados conserva el fondo de aviso y la tinta.
describe("botón «Demostración» en la barra oscura", () => {
  const fuente = leer("shell/MarcaDemostracion.scss");
  const selector = ".silice-marco-barra .silice-demo .silice-demo__boton";

  test("tiene una regla con más especificidad que los estados de Carbon", () => {
    expect(fuente).toContain(`${selector},`);
  });

  test.each([":hover", ":active", ":focus-visible", '[aria-expanded="true"]'])(
    "en el estado %s conserva el fondo de aviso y la tinta",
    (estado) => {
      expect(fuente).toContain(`${selector}${estado}`);
    },
  );

  test("la regla de esos estados fija el fondo de aviso y el texto primario", () => {
    const i = fuente.indexOf(selector);
    const regla = fuente.slice(i, fuente.indexOf("}", i));
    expect(regla).toMatch(/background(-color)?:\s*var\(--silice-aviso-fondo\)/);
    expect(regla).toMatch(/color:\s*var\(--cds-text-primary\)/);
  });
});
