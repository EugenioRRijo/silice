import { render, screen, within } from "@testing-library/react";
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
  { codigo: "INS-3", descripcion: "Arena ficticia", tipo: "material", unidad: "m3", precio_vigente: "0.50" },
  { codigo: "INS-4", descripcion: "Bloque ficticio", tipo: "material", unidad: "m2", precio_vigente: "2000" },
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

  test("los insumos traen el precio en es-VE, la unidad escrita y un texto si no hay precio vigente", async () => {
    const usuario = userEvent.setup();
    montar();
    await screen.findByRole("table", { name: "Partidas" });
    await usuario.click(screen.getByRole("tab", { name: /Insumos/ }));
    const tabla = await screen.findByRole("table", { name: "Insumos" });
    const fila = (codigo: string) => within(tabla).getByText(codigo).closest("tr") as HTMLElement;
    expect(fila("INS-1")).toHaveTextContent("12,3400");
    expect(fila("INS-3")).toHaveTextContent("0,50");
    expect(fila("INS-3")).toHaveTextContent("m³");
    expect(fila("INS-4")).toHaveTextContent("2.000");
    expect(fila("INS-4")).toHaveTextContent("m²");
    expect(fila("INS-2")).toHaveTextContent("Sin precio vigente");
    expect(tabla).not.toHaveTextContent(/\d\.\d{2}(?!\d)/);
    expect(tabla).not.toHaveTextContent(/m[23]/);
  });

  test("las partidas escriben la unidad con superindice", async () => {
    montar();
    const tabla = await screen.findByRole("table", { name: "Partidas" });
    expect(tabla).toHaveTextContent("m³");
    expect(tabla).not.toHaveTextContent(/m3/);
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
    // Mientras carga el h1 ya esta (V-8); se espera a la tabla para comprobar el de la pagina completa.
    expect(screen.getByRole("heading", { level: 1, name: "Catálogo de partidas e insumos" })).toBeInTheDocument();
    await screen.findByRole("table", { name: "Partidas" });
    expect(screen.getByRole("heading", { level: 1, name: "Catálogo de partidas e insumos" })).toBeInTheDocument();
  });
});
