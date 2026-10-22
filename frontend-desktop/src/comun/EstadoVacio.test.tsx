import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { EstadoVacio } from "./EstadoVacio";

describe("EstadoVacio", () => {
  test("dice que falta y que hacer, y deja poner una accion", () => {
    render(
      <EstadoVacio titulo="Todavía no hay partidas" descripcion="Cree la primera desde Elaborar un presupuesto.">
        <button type="button">Elaborar un presupuesto</button>
      </EstadoVacio>,
    );
    expect(screen.getByText("Todavía no hay partidas")).toBeInTheDocument();
    expect(screen.getByText(/Cree la primera/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Elaborar un presupuesto" })).toBeInTheDocument();
  });

  test("la descripcion es opcional", () => {
    render(<EstadoVacio titulo="Sin resultados" />);
    expect(screen.getByText("Sin resultados")).toBeInTheDocument();
  });
});
