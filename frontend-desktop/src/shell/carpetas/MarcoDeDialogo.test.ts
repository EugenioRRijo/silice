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

  test("la señal es una gradiente al pie (no un fondo del contenedor, que tapan los campos) y una barra visible", () => {
    const fuente = leer("shell/carpetas/MarcoDeDialogo.scss");
    expect(cuerpo).not.toMatch(/background-attachment/);
    // Tercera pasada (31-10): la gradiente al blanco del fondo no se notaba sobre un campo blanco; va a gris y con raya.
    expect(reglaDe(fuente, ".silice-dialogo__zona--mas-abajo::after")).toMatch(/linear-gradient\(to bottom, transparent, var\(--cds-layer-accent-01\)\)/);
    expect(reglaDe(fuente, ".silice-dialogo__zona--mas-abajo::after")).toMatch(/border-block-end:\s*2px solid var\(--cds-border-strong-01\)/);
    expect(reglaDe(fuente, ".silice-dialogo__zona--mas-abajo::after")).toMatch(/pointer-events:\s*none/);
    expect(cuerpo).toMatch(/scrollbar-color:\s*var\(--cds-border-strong\)/);
  });
});

describe("el componente de la receta", () => {
  const scss = leer("paginas/produccion/planta.scss");

  test("su fila reparte los campos en una sola línea y alinea «Quitar» con ellos", () => {
    expect(reglaDe(scss, ".receta-componente")).toMatch(/grid-template-columns:[^;]*auto\s*;/);
    expect(scss).toMatch(/\.receta-componente[^}]*\.receta-componente__quitar|\.receta-componente__quitar\s*\{[^}]*align-self/s);
  });
});

describe("los selectores de unidad y tipo de la receta no recortan «Elija la unidad»", () => {
  test("sus columnas tienen un mínimo en rem para que quepa el texto y la flecha", () => {
    const rejilla = reglaDe(leer("paginas/produccion/planta.scss"), ".receta-componente");
    expect(rejilla).toMatch(/repeat\(2,\s*minmax\(11rem,/);
  });
});

// El aviso verde que recibe el foco (Tramos, Receta, Costos): su caja enfocada no puede verse como un recuadro negro más
// ancho que el aviso.
describe("la caja del aviso con foco", () => {
  const aviso = reglaDe(leer("comun/comun.scss"), ".silice-aviso-foco");
  const enfocada = reglaDe(leer("comun/comun.scss"), ".silice-aviso-foco:focus");

  test("mide lo que el aviso, no todo el ancho", () => {
    expect(aviso).toMatch(/inline-size:\s*fit-content/);
  });

  test("su foco usa el anillo del tema, por dentro", () => {
    expect(enfocada).toMatch(/outline:\s*2px solid var\(--cds-focus\)/);
    expect(enfocada).toMatch(/outline-offset:\s*-2px/);
  });
});
