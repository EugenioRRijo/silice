import { describe, expect, test } from "vitest";

// jsdom no calcula CSS: las reglas se leen del fuente (como marco/estilosMarco.test.ts) y se midieron en el navegador.
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const leer = (ruta: string) => nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/${ruta}`, "utf-8");

function reglaDe(fuente: string, selector: string): string {
  const i = fuente.indexOf(`${selector} {`);
  if (i < 0) return "";
  const abre = fuente.indexOf("{", i);
  return fuente.slice(i, fuente.indexOf("}", abre));
}

// Pasada de navegador a 1366x768 (31-10): «Registrar un costo» y «Registrar una receta nueva» quedaban cortados contra el pie
// sin ninguna señal de que había más debajo.
describe("el cuerpo de un diálogo se desplaza y lo dice", () => {
  const cuerpo = reglaDe(leer("shell/carpetas/MarcoDeDialogo.scss"), ".silice-dialogo__cuerpo");

  test("se desplaza solo, entre el título y el pie", () => {
    expect(cuerpo).toMatch(/overflow-y:\s*auto/);
  });

  test("lleva una sombra de desplazamiento arriba y abajo que solo se ve cuando hay más contenido", () => {
    expect(cuerpo).toMatch(/background-attachment:[^;]*local/);
    expect(cuerpo).toMatch(/linear-gradient/);
  });
});

describe("el componente de la receta", () => {
  const scss = leer("paginas/produccion/planta.scss");

  test("su fila reparte los campos en una sola línea y alinea «Quitar» con ellos", () => {
    expect(reglaDe(scss, ".receta-componente")).toMatch(/grid-template-columns:[^;]*auto\s*;/);
    expect(scss).toMatch(/\.receta-componente[^}]*\.receta-componente__quitar|\.receta-componente__quitar\s*\{[^}]*align-self/s);
  });
});
