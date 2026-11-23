import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, test } from "vitest";
import { LanzadorDeEspacio } from "./LanzadorDeEspacio";

// Un lanzador de la Vista general (rediseño 2026-11-21): se llama como su espacio y lo describe con las herramientas que la
// cuenta puede usar allí. Sin herramientas que decir no apunta a una descripción vacía. Oráculos escritos a mano.
function montar(herramientas: string) {
  return render(
    <MemoryRouter>
      <LanzadorDeEspacio id="precios" titulo="Precios y catálogo" ruta="/precios/catalogo" herramientas={herramientas} />
    </MemoryRouter>,
  );
}

describe("LanzadorDeEspacio", () => {
  test("se llama como su espacio y su descripción son las herramientas que puede usar, sin numeración ni «Ventana dedicada»", () => {
    const { container } = montar("Catálogo de partidas e insumos · Simulador de listas");
    const enlace = screen.getByRole("link", { name: "Precios y catálogo" });
    expect(enlace).toHaveAttribute("href", "/precios/catalogo");
    expect(enlace).toHaveAccessibleDescription("Catálogo de partidas e insumos · Simulador de listas");
    expect(enlace.textContent).not.toMatch(/ventana dedicada|\b0[123]\s*·/i);
    expect(container.querySelector(".silice-lanzador__codigo")).toBeNull();
  });

  test("sin herramientas que decir no apunta a una descripción vacía", () => {
    const { container } = montar("");
    const enlace = screen.getByRole("link", { name: "Precios y catálogo" });
    expect(enlace).not.toHaveAttribute("aria-describedby");
    expect(container.querySelector(".silice-lanzador__desc")).toBeNull();
  });
});
