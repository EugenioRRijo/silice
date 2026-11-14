import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";
import type { Evaluacion } from "./cliente";
import { PanelDesglose } from "./PanelDesglose";
import { TablaInsumos } from "./TablaInsumos";
import { COLUMNAS, filaVacia, normalizarFila } from "./tablas";

// F5 vial, tarea 3: el desperdicio de un material (diseño 2026-11-03 §4, opción B). Se teclea la cantidad neta y el
// porcentaje; el servidor calcula la cantidad con desperdicio y la leyenda «0,52 (0,50 + 4 %)»: aquí no se calcula nada.
// Una fila sin desperdicio no lleva la clave, así lo que viaja de las filas de siempre no cambia. Datos ficticios.
describe("Desperdicio en Componer", () => {
  test("los materiales tienen la columna «Desperdicio (%)», opcional en la fila", () => {
    expect(COLUMNAS.materiales.map((c) => c.titulo)).toEqual(["Descripción", "Unidad", "Consumo por unidad", "Desperdicio (%)", "Precio"]);
    expect(filaVacia("materiales")).toEqual({ descripcion: "", unidad: "", cantidad: "", precio: "" });
    expect(normalizarFila("materiales", { descripcion: "Ligante", cantidad: "0,50", desperdicio: "4" })).toEqual({
      descripcion: "Ligante",
      unidad: "",
      cantidad: "0,50",
      precio: "",
      desperdicio: "4",
    });
    expect(normalizarFila("materiales", { descripcion: "Arena", desperdicio: "" })).not.toHaveProperty("desperdicio");
  });

  test("se teclea en su celda", async () => {
    const usuario = userEvent.setup();
    const alCambiar = vi.fn();
    render(
      <TablaInsumos
        tipo="materiales"
        filas={[{ descripcion: "Ligante ficticio", unidad: "l", cantidad: "0,50", precio: "2,00" }]}
        modalidades={[]}
        alCambiar={alCambiar}
        alAgregar={vi.fn()}
        alBorrar={vi.fn()}
        alExpirar={vi.fn()}
        alCompletar={vi.fn()}
      />,
    );
    expect(screen.getByRole("columnheader", { name: "Desperdicio (%)" })).toBeInTheDocument();
    await usuario.type(screen.getByRole("textbox", { name: "Desperdicio (%), fila 1" }), "4");
    expect(alCambiar).toHaveBeenCalledWith(0, "desperdicio", "4");
  });

  test("el desglose dice la cantidad con desperdicio que calculó el servidor", () => {
    const evaluacion: Evaluacion = {
      estado: "valido",
      aviso: null,
      desglose: { materiales: "1.04", equipos: "0.00", mano_obra: "0.00", costo_directo: "1.04", con_administracion: "1.20", precio_unitario: "1.32" },
      advertencias: [],
      requiere_justificacion: false,
      contraste: null,
      desperdicios: [{ fila: 1, descripcion: "Ligante ficticio", leyenda: "0,52 (0,50 + 4 %)" }],
    };
    render(<PanelDesglose evaluacion={evaluacion} cargando={false} error={null} />);
    expect(screen.getByRole("list", { name: "Materiales con desperdicio" })).toHaveTextContent(
      "Ligante ficticio (fila 1): consume 0,52 (0,50 + 4 %)",
    );
  });
});
