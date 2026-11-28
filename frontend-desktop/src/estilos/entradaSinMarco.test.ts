import { describe, expect, test } from "vitest";

// Revisión visual en claro y oscuro (T3, 2026-11-28, 1366 px): «Crear una cuenta» y «Tengo un código» (las pantallas sin
// marco que no son «Entrar») dibujaban su tarjeta pegada al borde izquierdo, con 709 px de ancho y todo el resto de la
// ventana vacío. «Entrar» sí queda centrada (su rejilla va con `place-items: center`). jsdom no calcula CSS: se lee la regla.
const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const app = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/estilos/app.scss`, "utf-8");

function reglaDe(fuente: string, selector: string): string {
  const i = fuente.indexOf(`\n${selector} {`);
  if (i < 0) throw new Error(`No hay una regla para ${selector}`);
  const abre = fuente.indexOf("{", i);
  return fuente.slice(abre, fuente.indexOf("}", abre));
}

describe("las pantallas sin marco que no son «Entrar»", () => {
  test("la tarjeta de «Crear una cuenta» y «Tengo un código» se centra en la ventana", () => {
    const entrada = reglaDe(app, ".silice-entrada");
    expect(entrada).toMatch(/margin-inline:\s*auto/);
    expect(entrada).toMatch(/max-inline-size:\s*38rem/);
  });
});

// T3 (2026-11-28), medido en el navegador a 1366 px: el cuadro «S» y «Sílice» quedaban a 2 px (el `gap` estaba en el
// anchor y Carbon envuelve su contenido en un solo `<span>`), y «Volver» (botón fantasma de Carbon, con 14 px de relleno
// a cada lado) arrancaba sangrado frente al borde izquierdo de los campos.
describe("la cabecera y las acciones de las pantallas sin marco", () => {
  test("la marca separa el sello y la palabra con un gap propio, en un contenedor flex", () => {
    const marca = reglaDe(app, ".silice-sin-marco__marca");
    expect(marca).toMatch(/display:\s*inline-flex/);
    expect(marca).toMatch(/align-items:\s*center/);
    expect(marca).toMatch(/gap:\s*0\.5rem/);
  });

  test("«Volver» (botón fantasma) compensa su relleno para alinear el texto con el borde de los campos", () => {
    const volver = reglaDe(app, ".silice-entrada__acciones > .cds--btn--ghost");
    expect(volver).toMatch(/margin-inline-start:\s*-0\.875rem/);
  });
});

