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

  // MENOR 10 del árbitro final: un aviso que sustituye a la pantalla lleva el h1 como los demás h1 de pantalla.
  test("con `nivel` 1 el título es el h1 de pantalla (heading-04, como los demás h1)", () => {
    render(<EstadoVacio titulo="Sin permiso" nivel={1} />);
    const h1 = screen.getByRole("heading", { level: 1, name: "Sin permiso" });
    expect(h1).toHaveClass("silice-vacio__titulo", "cds--type-heading-04");
    expect(h1).not.toHaveClass("cds--type-heading-compact-01");
  });

  test.each([2, 3] as const)("nivel %i conserva el aspecto compacto", (nivel) => {
    render(<EstadoVacio titulo="Sin permiso" nivel={nivel} />);
    expect(screen.getByRole("heading", { level: nivel, name: "Sin permiso" })).toHaveClass("silice-vacio__titulo", "cds--type-heading-compact-01");
  });

  test("por omisión el párrafo del título conserva el aspecto compacto", () => {
    render(<EstadoVacio titulo="Sin resultados" />);
    expect(screen.getByText("Sin resultados")).toHaveClass("cds--type-heading-compact-01");
  });
});
