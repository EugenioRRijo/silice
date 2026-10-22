import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, test } from "vitest";
import { MenuLateral } from "./MenuLateral";
import { SelectorProyecto } from "./Selectores";

const PROYECTOS = [
  { codigo: "P-01", nombre: "Clínica Norte con un nombre larguísimo que se recorta", version_vigente: 3, actualizado: null },
  { codigo: "P-02", nombre: "Galpón", version_vigente: null, actualizado: null },
];

// Con la letra grande el selector se acota (min(13rem, 18vw)) y el nombre del proyecto se recorta con puntos suspensivos:
// el nombre completo queda en el título.
describe("SelectorProyecto", () => {
  test("el título del selector trae el nombre completo del proyecto elegido", () => {
    render(<SelectorProyecto proyectos={PROYECTOS} elegido="P-01" alElegir={() => {}} />);
    expect(screen.getByRole("combobox", { name: "Proyecto" })).toHaveAttribute("title", PROYECTOS[0].nombre);
  });

  // Carbon fija el título solo al montar y al cambiar con el selector: si el proyecto cambia desde fuera, hay que dárselo.
  test("el título sigue al proyecto elegido cuando este cambia desde fuera", () => {
    const { rerender } = render(<SelectorProyecto proyectos={PROYECTOS} elegido="P-01" alElegir={() => {}} />);
    rerender(<SelectorProyecto proyectos={PROYECTOS} elegido="P-02" alElegir={() => {}} />);
    expect(screen.getByRole("combobox", { name: "Proyecto" })).toHaveAttribute("title", "Galpón");
  });

  test("sin proyecto elegido el título dice «Sin proyecto»", () => {
    render(<SelectorProyecto proyectos={PROYECTOS} elegido={null} alElegir={() => {}} />);
    expect(screen.getByRole("combobox", { name: "Proyecto" })).toHaveAttribute("title", "Sin proyecto");
  });
});

describe("MenuLateral, pie con la persona", () => {
  test("el menú trae al pie quién tiene la sesión (se ve cuando el menú es capa y la cabecera cede el nombre)", () => {
    render(
      <MemoryRouter>
        <MenuLateral paginas={[]} acciones={[]} modoEntrega={false} abierto alCerrar={() => {}} nombre="Ana Pérez" />
      </MemoryRouter>,
    );
    expect(screen.getByText("Sesión de Ana Pérez")).toBeInTheDocument();
  });

  test("sin nombre no hay pie", () => {
    render(
      <MemoryRouter>
        <MenuLateral paginas={[]} acciones={[]} modoEntrega={false} abierto alCerrar={() => {}} />
      </MemoryRouter>,
    );
    expect(screen.queryByText(/^Sesión de/)).not.toBeInTheDocument();
  });
});
