import { render, screen, waitFor, within } from "@testing-library/react";
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
    // VB-19: la fecha se lee dd/mm/aaaa; los precios y la variacion, en es-VE con el texto de la API en el title
    expect(within(tabla).getByText("01/02/2026")).toHaveAttribute("title", "2026-02-01");
    expect(within(tabla).getByText("10,6250")).toHaveAttribute("title", "10.6250");
    expect(within(tabla).getByText("10,0000")).toHaveAttribute("title", "10.0000");
    expect(within(tabla).getByText("6,25")).toBeInTheDocument();
    expect(tabla).not.toHaveTextContent("2026-02-01");
    expect(fetchFalso.mock.calls[0][0]).toBe("/cambios-precio");
  });

  test("los filtros de fecha son selectores de fecha y se envian AAAA-MM-DD (VB-19)", async () => {
    montar();
    await screen.findByRole("table", { name: "Cambios de precio" });
    expect(screen.getByLabelText("Desde")).toHaveAttribute("type", "date");
    expect(screen.getByLabelText("Hasta")).toHaveAttribute("type", "date");
    expect(screen.queryByLabelText(/AAAA-MM-DD/)).toBeNull();
  });

  test("filtra por insumo y fechas validas", async () => {
    const usuario = userEvent.setup();
    montar();
    await screen.findByRole("table", { name: "Cambios de precio" });
    await usuario.type(screen.getByLabelText("Insumo (descripción exacta)"), "Cemento ficticio");
    await usuario.type(screen.getByLabelText("Desde"), "2026-01-01");
    await usuario.click(screen.getByRole("button", { name: "Filtrar" }));
    await waitFor(() =>
      expect(fetchFalso).toHaveBeenLastCalledWith(
        "/cambios-precio?insumo=Cemento+ficticio&desde=2026-01-01",
        expect.anything(),
      ),
    );
  });

  test("un rango invertido avisa y no consulta", async () => {
    const usuario = userEvent.setup();
    montar();
    await screen.findByRole("table", { name: "Cambios de precio" });
    await usuario.type(screen.getByLabelText("Desde"), "2026-03-01");
    await usuario.type(screen.getByLabelText("Hasta"), "2026-02-01");
    expect(screen.getByText("Rango invertido")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Filtrar" }));
    expect(fetchFalso).toHaveBeenCalledTimes(1);
  });
  test.each([
    [404, "No existe el histórico en este caso."],
    [403, "Su cuenta no tiene permiso para el histórico."],
  ])("con %i de la API muestra el detalle y no se queda cargando", async (estado, detalle) => {
    fetchFalso.mockImplementation(() => Promise.resolve(json({ detail: detalle }, estado)));
    montar();
    expect(await screen.findByText(detalle)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  test("con un error de red muestra un aviso en vez del esqueleto", async () => {
    fetchFalso.mockRejectedValue(new TypeError("Failed to fetch"));
    montar();
    expect((await screen.findAllByRole("alert")).length).toBeGreaterThan(0);
  });

  test("el título de la página es un h1", async () => {
    montar();
    expect(await screen.findByRole("heading", { level: 1, name: "Histórico de cambios de precio" })).toBeInTheDocument();
  });
});
