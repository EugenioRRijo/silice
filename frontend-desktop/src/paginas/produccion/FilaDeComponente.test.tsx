import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { FilaDeComponente } from "./FilaDeComponente";

// Segunda pasada de navegador (31-10): el subrayado de «Código» quedaba 10 px más alto que el de los demás campos de la fila
// porque el campo con búsqueda se pintaba en tamaño pequeño (32 px) junto a campos de 40 px.
describe("la fila de un componente de la receta", () => {
  test("el código mide lo mismo que los demás campos de la fila (tamaño mediano)", () => {
    render(
      <FilaDeComponente
        numero={1}
        base="r"
        fila={{ codigo: "", cantidad: "", unidad: "", tipo: "" }}
        sePuedeQuitar
        puedeMarcarLigante={false}
        alCambiar={() => {}}
        alQuitar={() => {}}
        alExpirar={() => {}}
      />,
    );
    const codigo = document.getElementById("r-codigo") as HTMLElement;
    expect(codigo.className).toContain("cds--text-input--md");
    expect(codigo.className).not.toContain("cds--text-input--sm");
    expect((document.getElementById("r-cantidad") as HTMLElement).className).toContain("cds--text-input");
  });

  // Tarea 16c: la casilla del ligante es un control con nombre y solo la ve quien puede registrar recetas.
  test.each([
    [true, 1],
    [false, 0],
  ])("con puedeMarcarLigante=%s hay %i casillas «Es el ligante»", (puede, cuantas) => {
    render(
      <FilaDeComponente
        numero={1}
        base="r"
        fila={{ codigo: "CA-30", cantidad: "", unidad: "t", tipo: "comprado", esLigante: true }}
        sePuedeQuitar
        puedeMarcarLigante={puede}
        alCambiar={() => {}}
        alQuitar={() => {}}
        alExpirar={() => {}}
      />,
    );
    const casillas = screen.queryAllByRole("checkbox", { name: "Es el ligante" });
    expect(casillas).toHaveLength(cuantas);
    if (puede) expect(casillas[0]).toBeChecked();
  });
});
