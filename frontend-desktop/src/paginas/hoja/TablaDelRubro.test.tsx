import { render, screen, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { TablaDelRubro } from "./TablaDelRubro";
import type { GrupoApu } from "./logica";
import { sembrarApu } from "./logicaApu";

// F5 vial, punto 1 (lo que faltaba): la tabla de Materiales de la Hoja muestra la neta y el porcentaje de desperdicio que
// el servidor manda en `detalle.desperdicios` («0,50 + 4 %», ya escrito con coma decimal), junto a la cantidad que ya los
// incluye. La interfaz no calcula: si el usuario escribe otra cantidad, la traza ya no es de esa línea y no se muestra.
// Datos ficticios.

const m = (texto: string) => ({ texto, exacto: texto });

const MATERIALES: GrupoApu = {
  clave: "materiales",
  rotulo: "Materiales",
  columnas: [
    { clave: "descripcion", rotulo: "Descripción" },
    { clave: "unidad", rotulo: "Unidad" },
    { clave: "cantidad", rotulo: "Cantidad" },
    { clave: "precio", rotulo: "Precio" },
  ],
  filas: [
    { descripcion: "Arena ficticia", unidad: "m3", cantidad: "1,2", precio: "10" },
    { descripcion: "Ligante ficticio", unidad: "l", cantidad: "0,52", precio: "2,00" },
  ],
  subtotal: m("13.04"),
};

function pintar(desperdicios?: Array<{ fila: number; texto: string }>, cantidades?: string[]) {
  const edicion = sembrarApu({ rendimiento: "1", grupos: [MATERIALES] });
  if (cantidades) edicion.cantidades.materiales = cantidades;
  render(
    <TablaDelRubro
      grupo={MATERIALES}
      moneda="USD"
      edicion={edicion}
      ubicacion={null}
      idDelError="error"
      quitable={false}
      soloLectura
      desperdicios={desperdicios}
      alCambiar={vi.fn()}
      alRestaurar={vi.fn()}
      alQuitar={vi.fn()}
      alCambiarInsumo={vi.fn()}
    />,
  );
  return screen.getByRole("table", { name: /Materiales/ });
}

describe("TablaDelRubro: el desperdicio de los materiales", () => {
  test("sin desperdicios no hay columna nueva", () => {
    const tabla = pintar([]);
    expect(within(tabla).queryByRole("columnheader", { name: /desperdicio/i })).toBeNull();
  });

  test("la fila con traza muestra su neta y su porcentaje junto a la cantidad", () => {
    const tabla = pintar([{ fila: 2, texto: "0,50 + 4 %" }]);
    const cabeceras = within(tabla)
      .getAllByRole("columnheader")
      .map((c) => c.textContent?.trim());
    expect(cabeceras.indexOf("Neta + desperdicio")).toBe(cabeceras.indexOf("Cantidad") + 1);
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(within(filas[1]!).getByText("0,50 + 4 %")).toBeTruthy();
    expect(within(filas[0]!).queryByText(/%/)).toBeNull();
  });

  test("si se escribe otra cantidad, la traza ya no se muestra", () => {
    const tabla = pintar([{ fila: 2, texto: "0,50 + 4 %" }], ["1,2", "0,60"]);
    expect(within(tabla).queryByText("0,50 + 4 %")).toBeNull();
  });
});
