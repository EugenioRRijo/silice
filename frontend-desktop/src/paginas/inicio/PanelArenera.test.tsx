import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, test } from "vitest";
import { PanelArenera } from "./PanelArenera";
import type { ExistenciaRespuesta } from "./PanelArenera";

const GRANZON: ExistenciaRespuesta = {
  codigo: "GRA-01",
  nombre: "Granzón",
  unidad_venta: "m3",
  existencia: "-4.25", // como lo manda el servidor (texto decimal con punto)
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

// Prueba en vivo 2026-11-18 (frente D): la existencia salía «32,00 t» junto a una mínima de «40 t». Las dos se leen como
// en Existencias (`cantidadEsVe`): sin ceros de más, en la misma escala.
describe("PanelArenera: la existencia y la mínima en la misma escala", () => {
  test("«32.00» y «40» se leen «32 t» y «40 t»", () => {
    const arena: ExistenciaRespuesta = {
      codigo: "ARE-01",
      nombre: "Arena lavada",
      unidad_venta: "t",
      existencia: "32.00",
      minima: "40",
      queda_poco: true,
      negativa: false,
    };
    render(
      <MemoryRouter>
        <PanelArenera carga={{ estado: "listo", datos: [arena] }} />
      </MemoryRouter>,
    );
    const fila = within(screen.getByRole("table")).getByRole("row", { name: /Arena lavada/ });
    const celdas = within(fila).getAllByRole("cell");
    expect(celdas[1]!.textContent).toBe("32 t");
    expect(celdas[2]!.textContent).toBe("40 t");
  });
});

describe("PanelArenera: sin permiso dice a quién pedirlo", () => {
  test("un 403 nombra los papeles que ven la arenera", () => {
    render(
      <MemoryRouter>
        <PanelArenera carga={{ estado: "sin_permiso", error: null }} />
      </MemoryRouter>,
    );
    expect(screen.getByText("Sin datos de la arenera para su cuenta")).toBeInTheDocument();
    expect(
      screen.getByText("Ver la arenera pide el papel «arma presupuestos» o «administra la instalación»: pídaselo a quien administra Sílice."),
    ).toBeInTheDocument();
  });
});
