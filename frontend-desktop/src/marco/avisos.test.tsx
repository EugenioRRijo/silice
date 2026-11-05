import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { AvisoApagada, AvisoSinPermiso, MENSAJE_APAGADA, MENSAJE_SIN_PERMISO } from "./avisos";

// Pasada en el navegador de F6 (H9): una pantalla que la cuenta no puede usar quedaba sin h1. El aviso es el título de la
// pantalla (un h1), salvo donde la página ya trae el suyo (la Cuenta: el h1 es el de la sección y el aviso va en h2).
describe("avisos de pantalla que no se puede usar", () => {
  test("«Sin permiso» es el h1 de la pantalla, con su mensaje", () => {
    render(<AvisoSinPermiso />);
    expect(screen.getByRole("heading", { level: 1, name: "Sin permiso" })).toBeInTheDocument();
    expect(screen.getByText(MENSAJE_SIN_PERMISO)).toBeInTheDocument();
  });

  test("«Apagada» es el h1 de la pantalla, con su mensaje", () => {
    render(<AvisoApagada />);
    expect(screen.getByRole("heading", { level: 1, name: "Apagada" })).toBeInTheDocument();
    expect(screen.getByText(MENSAJE_APAGADA)).toBeInTheDocument();
  });

  test("donde la página ya tiene su h1, el aviso baja a h2 y no hay dos h1", () => {
    render(
      <>
        <h1>Cuentas y permisos</h1>
        <AvisoSinPermiso nivel={2} />
      </>,
    );
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 2, name: "Sin permiso" })).toBeInTheDocument();
  });
});
