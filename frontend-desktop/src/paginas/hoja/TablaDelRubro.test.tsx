import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import { TablaDelRubro } from "./TablaDelRubro";
import type { DesperdicioDeApu, GrupoApu } from "./logica";
import { sembrarApu } from "./logicaApu";
import type { UbicacionDeApu } from "./logicaApu";

// F5 vial: la tabla de Materiales edita la neta y «Desperdicio (%)»; el servidor devuelve la cantidad con desperdicio
// en `f.cantidad` y su traza en `detalle.desperdicios`. La interfaz no calcula: si cambia la neta o el porcentaje
// escritos, «Cantidad con desperdicio» se oculta hasta que el servidor recalcule. Datos ficticios.

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

const TRAZA: DesperdicioDeApu = { fila: 2, texto: "0,50 + 4 %", neta: "0,50", porcentaje: "4" };

function pintar({
  desperdicios = [],
  cantidades,
  porcentajes,
  ubicacion = null,
  conDesperdicio = true,
  soloLectura = false,
}: {
  desperdicios?: DesperdicioDeApu[];
  cantidades?: string[];
  porcentajes?: string[];
  ubicacion?: UbicacionDeApu | null;
  conDesperdicio?: boolean;
  soloLectura?: boolean;
} = {}) {
  const edicion = sembrarApu({ rendimiento: "1", grupos: [MATERIALES], desperdicios });
  if (cantidades) edicion.cantidades.materiales = cantidades;
  if (porcentajes) edicion.desperdicios = porcentajes;
  render(
    <>
      <div id="error">materiales, fila 2: el desperdicio «x» no se entiende como número.</div>
      <TablaDelRubro
        grupo={MATERIALES}
        moneda="USD"
        edicion={edicion}
        ubicacion={ubicacion}
        idDelError="error"
        quitable={false}
        soloLectura={soloLectura}
        conDesperdicio={conDesperdicio}
        desperdicios={desperdicios}
        alCambiar={vi.fn()}
        alRestaurar={vi.fn()}
        alCambiarDesperdicio={vi.fn()}
        alRestaurarDesperdicio={vi.fn()}
        alQuitar={vi.fn()}
        alCambiarInsumo={vi.fn()}
      />
    </>,
  );
  return screen.getByRole("table", { name: /Materiales/ });
}

describe("TablaDelRubro: el desperdicio de los materiales", () => {
  test("sin filas con desperdicio no hay columna «Cantidad con desperdicio» y sí «Desperdicio (%)»", () => {
    const tabla = pintar({ desperdicios: [] });
    expect(within(tabla).getByRole("columnheader", { name: "Desperdicio (%)" })).toBeTruthy();
    expect(within(tabla).queryByRole("columnheader", { name: "Cantidad con desperdicio" })).toBeNull();
  });

  test("la fila con desperdicio edita la neta y el porcentaje, y muestra la cantidad con desperdicio", () => {
    const tabla = pintar({ desperdicios: [TRAZA] });
    const cabeceras = within(tabla)
      .getAllByRole("columnheader")
      .map((c) => c.textContent?.trim());
    expect(cabeceras.indexOf("Desperdicio (%)")).toBe(cabeceras.indexOf("Cantidad") + 1);
    expect(cabeceras.indexOf("Cantidad con desperdicio")).toBe(cabeceras.indexOf("Desperdicio (%)") + 1);
    expect(within(tabla).getByRole("textbox", { name: "Cantidad, Materiales fila 1" })).toHaveValue("1,2");
    expect(
      within(tabla).getByRole("textbox", { name: "Desperdicio en porcentaje, Materiales fila 1" }),
    ).toHaveValue("");
    expect(within(tabla).getByRole("textbox", { name: "Cantidad neta, Materiales fila 2" })).toHaveValue("0,50");
    expect(
      within(tabla).getByRole("textbox", { name: "Desperdicio en porcentaje, Materiales fila 2" }),
    ).toHaveValue("4");
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(within(filas[1]!).getByText("0,52")).toBeTruthy();
    expect(within(filas[0]!).queryByText("0,52")).toBeNull();
  });

  test("si se escribe otra neta o porcentaje, «Cantidad con desperdicio» de esa fila se oculta", () => {
    const tablaNeta = pintar({ desperdicios: [TRAZA], cantidades: ["1,2", "0,60"] });
    expect(within(tablaNeta).queryByText("0,52")).toBeNull();
    const tablaPct = pintar({ desperdicios: [TRAZA], porcentajes: ["", "5"] });
    expect(within(tablaPct).queryByText("0,52")).toBeNull();
  });

  test("un error ubicado en el desperdicio marca ese campo con aria-invalid y lo liga al id del error", () => {
    const tabla = pintar({ desperdicios: [TRAZA], ubicacion: { campo: "desperdicio", fila: 2 } });
    const campo = within(tabla).getByRole("textbox", { name: "Desperdicio en porcentaje, Materiales fila 2" });
    expect(campo).toHaveAttribute("aria-invalid", "true");
    expect(campo).toHaveAttribute("aria-describedby", "error");
    expect(within(tabla).getByRole("textbox", { name: "Cantidad neta, Materiales fila 2" })).not.toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(
      within(tabla).getByRole("textbox", { name: "Desperdicio en porcentaje, Materiales fila 1" }),
    ).not.toHaveAttribute("aria-invalid", "true");
  });

  test("flechas arriba y abajo mueven el foco entre filas de la columna de desperdicio", async () => {
    const tabla = pintar({ desperdicios: [TRAZA] });
    const u = userEvent.setup();
    const fila1 = within(tabla).getByRole("textbox", { name: "Desperdicio en porcentaje, Materiales fila 1" });
    const fila2 = within(tabla).getByRole("textbox", { name: "Desperdicio en porcentaje, Materiales fila 2" });
    fila1.focus();
    await u.keyboard("{ArrowDown}");
    expect(fila2).toHaveFocus();
    await u.keyboard("{ArrowUp}");
    expect(fila1).toHaveFocus();
  });
});
