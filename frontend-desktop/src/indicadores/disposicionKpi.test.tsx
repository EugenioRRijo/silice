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
  const desde = estilos.lastIndexOf(`\n${selector} {`);
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

  test("la tarjeta con la frase completa del libro menor se lleva mas ancho que las de marcador breve (menos lineas, menos alto)", () => {
    const menor = { clave: "T", titulo: "Total", actual: "1.00", meta: "2.00", delta: "-1.00", delta_pct: "-50.00", sentido: "exactitud" as const };
    const { container, rerender } = render(<IndicadorFiori indicador={menor} partidasConOmision={[2]} />);
    expect(container.querySelector(".fiori-kpi")).toHaveClass("fiori-kpi--frase");
    rerender(<IndicadorFiori indicador={menor} partidasConOmision={[2]} etiquetaBreve />);
    expect(container.querySelector(".fiori-kpi")).not.toHaveClass("fiori-kpi--frase");
    rerender(<IndicadorFiori indicador={{ ...menor, delta: "1.00" }} />);
    expect(container.querySelector(".fiori-kpi")).not.toHaveClass("fiori-kpi--frase");
    expect(regla(".fiori-kpi--frase")).toMatch(/flex:\s*2\.5 1 0/);
  });

  test("la variacion baja de linea en vez de recortarse con elipsis (las tarjetas con marcador son estrechas)", () => {
    expect(regla(".fiori-kpi__delta")).toMatch(/white-space:\s*normal/);
    expect(regla(".fiori-kpi__delta")).toMatch(/overflow:\s*visible/);
  });
});
