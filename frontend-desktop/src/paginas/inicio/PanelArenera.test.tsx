import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, test } from "vitest";
import { PanelArenera } from "./PanelArenera";
import type { ExistenciaRespuesta } from "./PanelArenera";

const GRANZON: ExistenciaRespuesta = {
  codigo: "GRA-01",
  nombre: "Granzón",
  unidad_venta: "m3",
  existencia: "-4,25",
  minima: "10",
  queda_poco: true,
  negativa: true,
};

describe("PanelArenera: las unidades se leen bien", () => {
  test("la existencia y la mínima dicen «m³», no «m3»", () => {
    render(
      <MemoryRouter>
        <PanelArenera carga={{ estado: "listo", datos: [GRANZON] }} />
      </MemoryRouter>,
    );
    const tabla = screen.getByRole("table", { name: "Materiales de la arenera que requieren atención" });
    const fila = within(tabla).getByRole("row", { name: /Granzón/ });
    const celdas = within(fila).getAllByRole("cell");
    expect(celdas[1]!.textContent).toBe("-4,25 m³");
    expect(celdas[2]!.textContent).toBe("10 m³");
  });
});
