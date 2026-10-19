import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaHistorico from "./index";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["lector"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["leer_proyecto"],
  modo_entrega: false,
};

const CAMBIOS = [
  { insumo: "Cemento ficticio", precio_anterior: "10.0000", precio_nuevo: "10.6250", variacion: "0.0625", fecha: "2026-02-01" },
];

describe("Histórico de cambios de precio", () => {
  const fetchFalso = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    fetchFalso.mockResolvedValue(json(CAMBIOS));
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  function montar() {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: { nombre: "clinica", ruta_relativa: "data/clinica.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter>
          <PaginaHistorico />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  test("lista los cambios con los montos de la API y la variacion en por ciento", async () => {
    montar();
    const tabla = await screen.findByRole("table", { name: "Cambios de precio" });
    expect(tabla).toHaveTextContent("10.6250");
    expect(tabla).toHaveTextContent("6.25");
    expect(fetchFalso.mock.calls[0][0]).toBe("/v1/cambios-precio");
  });

  test("filtra por insumo y fechas validas", async () => {
    const usuario = userEvent.setup();
    montar();
    await screen.findByRole("table", { name: "Cambios de precio" });
    await usuario.type(screen.getByLabelText("Insumo (descripción exacta)"), "Cemento ficticio");
    await usuario.type(screen.getByLabelText("Desde (AAAA-MM-DD)"), "2026-01-01");
    await usuario.click(screen.getByRole("button", { name: "Filtrar" }));
    await waitFor(() =>
      expect(fetchFalso).toHaveBeenLastCalledWith(
        "/v1/cambios-precio?insumo=Cemento+ficticio&desde=2026-01-01",
        expect.anything(),
      ),
    );
  });

  test("un rango invertido avisa y no consulta", async () => {
    const usuario = userEvent.setup();
    montar();
    await screen.findByRole("table", { name: "Cambios de precio" });
    await usuario.type(screen.getByLabelText("Desde (AAAA-MM-DD)"), "2026-03-01");
    await usuario.type(screen.getByLabelText("Hasta (AAAA-MM-DD)"), "2026-02-01");
    expect(screen.getByText("Rango invertido")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Filtrar" }));
    expect(fetchFalso).toHaveBeenCalledTimes(1);
  });
});
