import { render } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { IndicadorFiori } from "./IndicadorFiori";

const nodo = (
  globalThis as unknown as {
    process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
  }
).process;
const estilos = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/indicadores/indicadores.scss`, "utf-8");
const regla = (selector: string) => {
  const desde = estilos.indexOf(`\n${selector} {`);
  return desde < 0 ? "" : estilos.slice(desde, estilos.indexOf("}", desde));
};

// V-16: a Muy grande (150 %) la columna de la cifra se quedaba en 0 px (titulo y cifra invisibles) porque la variacion
// ocupaba todo el ancho. Cada par (titulo y meta; cifra y variacion) va en una fila que baja de linea si no caben.
describe("disposicion del indicador: la cifra nunca desaparece", () => {
  test("titulo y meta comparten una fila; cifra y variacion, otra", () => {
    const { container } = render(
      <IndicadorFiori
        indicador={{ clave: "T", titulo: "Total", actual: "1.00", meta: "2.00", delta: "-1.00", delta_pct: "-50.00", sentido: "exactitud" }}
      />,
    );
    const filas = [...container.querySelectorAll(".fiori-kpi__fila")];
    expect(filas).toHaveLength(2);
    expect(filas[0].querySelector(".fiori-kpi__titulo")).not.toBeNull();
    expect(filas[0].querySelector(".fiori-kpi__meta")).not.toBeNull();
    expect(filas[1].querySelector(".fiori-kpi__actual")).not.toBeNull();
    expect(filas[1].querySelector(".fiori-kpi__delta")).not.toBeNull();
  });

  test("la fila es flex con salto de linea, y la tarjeta no usa una rejilla de dos columnas", () => {
    expect(regla(".fiori-kpi__fila")).toMatch(/display:\s*flex/);
    expect(regla(".fiori-kpi__fila")).toMatch(/flex-wrap:\s*wrap/);
    expect(regla(".fiori-kpi")).not.toMatch(/grid-template-columns/);
  });
});
