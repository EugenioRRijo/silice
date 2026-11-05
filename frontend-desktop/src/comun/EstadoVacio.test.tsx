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

describe("EstadoVacio: el nivel del título", () => {
  test("por omisión el título es un párrafo, no un encabezado", () => {
    render(<EstadoVacio titulo="Sin resultados" />);
    expect(screen.queryByRole("heading")).toBeNull();
  });

  test("con `nivel` el título es un encabezado de ese nivel y conserva su aspecto", () => {
    render(<EstadoVacio titulo="Sin permiso" nivel={1} />);
    const h1 = screen.getByRole("heading", { level: 1, name: "Sin permiso" });
    expect(h1).toHaveClass("silice-vacio__titulo", "cds--type-heading-compact-01");
  });

  test("nivel 2 es un h2", () => {
    render(<EstadoVacio titulo="Sin permiso" nivel={2} />);
    expect(screen.getByRole("heading", { level: 2, name: "Sin permiso" })).toBeInTheDocument();
  });
});
