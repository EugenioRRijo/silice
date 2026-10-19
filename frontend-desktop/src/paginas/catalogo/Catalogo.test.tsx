import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaCatalogo from "./index";

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

const PARTIDAS = [
  { codigo: "CIV-001", descripcion: "Excavación manual", unidad: "m3", dominio: "civil" },
  { codigo: "CIV-002", descripcion: "Relleno compactado", unidad: "m3", dominio: "civil" },
];
const INSUMOS = [
  { codigo: "INS-1", descripcion: "Cemento ficticio", tipo: "material", unidad: "saco", precio_vigente: "12.3400" },
  { codigo: "INS-2", descripcion: "Peón ficticio", tipo: "mano_obra", unidad: null, precio_vigente: null },
];

describe("Catálogo de partidas e insumos", () => {
  const fetchFalso = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    fetchFalso.mockImplementation((ruta) =>
      Promise.resolve(json(String(ruta).endsWith("/partidas") ? PARTIDAS : INSUMOS)),
    );
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
          <PaginaCatalogo />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  test("muestra las partidas y la busqueda ignora tildes", async () => {
    const usuario = userEvent.setup();
    montar();
    const tabla = await screen.findByRole("table", { name: "Partidas" });
    expect(tabla).toHaveTextContent("Excavación manual");
    expect(tabla).toHaveTextContent("Relleno compactado");
    await usuario.type(screen.getByRole("searchbox", { name: "Buscar en el catálogo" }), "excavacion");
    expect(screen.getByRole("table", { name: "Partidas" })).not.toHaveTextContent("Relleno compactado");
  });

  test("los insumos traen el precio tal como llega y vacio si no hay lista vigente", async () => {
    const usuario = userEvent.setup();
    montar();
    await screen.findByRole("table", { name: "Partidas" });
    await usuario.click(screen.getByRole("tab", { name: /Insumos/ }));
    const tabla = await screen.findByRole("table", { name: "Insumos" });
    expect(tabla).toHaveTextContent("12.3400");
    expect(tabla).toHaveTextContent("Peón ficticio");
  });
  test.each([
    [404, "No existe el catálogo en este caso."],
    [403, "Su cuenta no tiene permiso para el catálogo."],
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
    expect(await screen.findByRole("heading", { level: 1, name: "Catálogo de partidas e insumos" })).toBeInTheDocument();
  });
});
