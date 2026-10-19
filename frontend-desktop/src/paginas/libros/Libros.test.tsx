import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaLibros from "./index";

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["lector"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["leer_proyecto"],
  modo_entrega: false,
};

describe("Libro de la empresa", () => {
  test("tiene su h1 y el visor queda dentro del marco de la página", () => {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: null,
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    const { container } = render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter>
          <PaginaLibros />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
    expect(screen.getByRole("heading", { level: 1, name: "Libro de la empresa" })).toBeInTheDocument();
    expect(container.querySelector(".silice-pagina-libro .visor")).not.toBeNull();
  });
});
