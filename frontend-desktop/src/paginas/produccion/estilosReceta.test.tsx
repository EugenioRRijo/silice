import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { FilaDeComponente } from "./FilaDeComponente";

// Prueba en vivo 2026-11-18 (frente D), «Registrar una receta» a 1440x900: «Código» y «Cantidad por t» colapsaban a
// ancho cero. La rejilla tenía dos pistas `minmax(0, …fr)` y una `auto` donde caía la casilla «Es el ligante», cuyo
// texto largo se comía el ancho. jsdom no calcula el diseño: aquí se fijan las reglas; el efecto se mide en navegador.

// Con `css: false` el `?raw` de un .scss llega vacío: se lee con el módulo de Node (como estilosBienvenida.test.ts).
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }).process;
const estilos = nodo
  .getBuiltinModule("node:fs")
  .readFileSync(`${nodo.cwd()}/src/paginas/produccion/planta.scss`, "utf-8")
  .replace(/\/\/.*$/gm, "");

// El cuerpo de la regla de primer nivel (al comienzo de una línea) cuyo selector es exactamente `selector`.
function regla(selector: string): string {
  const inicio = estilos.search(new RegExp(`^${selector.replace(/[.]/g, "\\.")} \\{`, "m"));
  expect(inicio, `falta la regla ${selector}`).toBeGreaterThanOrEqual(0);
  let nivel = 0;
  for (let i = estilos.indexOf("{", inicio); i < estilos.length; i++) {
    if (estilos[i] === "{") nivel++;
    if (estilos[i] === "}" && --nivel === 0) return estilos.slice(inicio, i + 1);
  }
  throw new Error(`regla sin cerrar: ${selector}`);
}

describe("la rejilla de un componente de la receta", () => {
  test("ninguna pista de la fila puede quedar en cero ni crecer con el contenido", () => {
    const columnas = /grid-template-columns:\s*([^;]+);/.exec(regla(".receta-componente"))?.[1] ?? "";
    expect(columnas).not.toBe("");
    expect(columnas).not.toMatch(/minmax\(\s*0/);
    expect(columnas).not.toMatch(/\bauto\b/);
  });

  test("la casilla del ligante va en su propia fila y «Quitar» en la última columna", () => {
    expect(regla(".receta-componente__ligante")).toMatch(/grid-column:\s*1\s*\/\s*-2\s*;/);
    expect(regla(".receta-componente__quitar")).toMatch(/grid-column:\s*-2\s*\/\s*-1\s*;/);
  });

  test("la casilla del ligante lleva la clase que la saca de la fila de los campos", () => {
    render(
      <FilaDeComponente
        numero={1}
        base="r"
        fila={{ codigo: "", cantidad: "", unidad: "", tipo: "" }}
        sePuedeQuitar
        puedeMarcarLigante
        alCambiar={() => {}}
        alQuitar={() => {}}
        alExpirar={() => {}}
      />,
    );
    const contenedor = document.querySelector(".receta-componente__ligante");
    expect(contenedor).not.toBeNull();
    expect(contenedor?.querySelector("#r-ligante")).not.toBeNull();
  });
});
