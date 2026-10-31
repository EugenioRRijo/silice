import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import ProducirMezcla from "./ProducirMezcla";

// Datos ficticios. La pantalla multiplica la receta por las toneladas solo para anunciar lo que consumirá; el servidor
// vuelve a calcularlo al registrar y es quien decide.
const ANA: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["operar_arenera"],
  modo_entrega: false,
};

function material(codigo: string, nombre: string, activo = true) {
  return { id: 1, codigo, nombre, unidad_venta: "t", densidad_t_m3: null, existencia_minima: "0", activo };
}
const MATERIALES = [material("AGR-12", "Agregado grueso"), material("MZP-01", "Mezcla propia uno"), material("MZP-VIEJA", "Mezcla sin receta")];
const RECETA = {
  id: 3,
  producto: "MZP-01",
  componentes: [
    { codigo: "AGR-12", cantidad_por_t: "0.94", unidad: "t", tipo: "propio" },
    { codigo: "CEM-01", cantidad_por_t: "0.06", unidad: "t", tipo: "comprado" },
  ],
  fuente: "Ensayo ficticio",
  vigente_desde: "2026-01-01",
};

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

describe("Producir mezcla", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let produccion: () => Response;
  let usuario: ReturnType<typeof userEvent.setup>;
  const alExpirar = vi.fn();

  function montar(sesion: SesionRespuesta = ANA) {
    render(
      <ContextoAplicacion.Provider value={{ sesion, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar }}>
        <MemoryRouter>
          <ProducirMezcla />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  const posts = () =>
    fetchFalso.mock.calls
      .filter((c) => c[1]?.method === "POST")
      .map((c) => ({ ruta: String(c[0]), cuerpo: c[1]?.body ? JSON.parse(String(c[1].body)) : null }));

  async function elegir(codigo = "MZP-01") {
    const lista = await screen.findByLabelText("Mezcla a producir");
    await waitFor(() => expect(within(lista).getByRole("option", { name: /MZP-01/ })).toBeInTheDocument());
    await usuario.selectOptions(lista, codigo);
  }

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 10, 15, 10, 0, 0));
    usuario = userEvent.setup();
    fijarCsrf("tok");
    alExpirar.mockReset();
    fetchFalso.mockReset();
    vi.stubGlobal("fetch", fetchFalso);
    produccion = () => json({ movimientos: [41, 42] }, 201);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      const metodo = init?.method ?? "GET";
      if (url.pathname === "/v1/produccion/materiales" && metodo === "GET") return json(MATERIALES);
      if (url.pathname === "/v1/produccion/recetas/vigente" && metodo === "GET") {
        return url.searchParams.get("producto") === "MZP-01" ? json(RECETA) : json({ detalle: "No hay receta vigente." }, 404);
      }
      if (url.pathname === "/v1/produccion/producciones" && metodo === "POST") return produccion();
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  test("tiene un solo h1 y ofrece solo los productos con receta vigente", async () => {
    montar();
    expect(screen.getByRole("heading", { level: 1, name: "Producir mezcla" })).toBeInTheDocument();
    await elegir();
    const lista = screen.getByLabelText("Mezcla a producir");
    expect(within(lista).getAllByRole("option").map((o) => o.textContent)).toEqual(["Elija la mezcla", "MZP-01 · Mezcla propia uno"]);
    expect(screen.getByLabelText("Fecha de la producción")).toHaveValue("2026-11-15");
  });

  test("elige la mezcla entre los productos con receta vigente y muestra lo que consumirá", async () => {
    montar();
    await elegir();
    await usuario.type(screen.getByLabelText("Toneladas producidas"), "2,5");
    const consumo = screen.getByRole("list", { name: "Lo que consumirá del inventario" });
    expect(within(consumo).getAllByRole("listitem").map((i) => i.textContent)).toEqual(["2,35 t de AGR-12"]);
  });

  test("toneladas con coma decimal y punto de miles: «1.234,5» se manda «1234.5»", async () => {
    montar();
    await elegir();
    await usuario.type(screen.getByLabelText("Toneladas producidas"), "1.234,5");
    await usuario.click(screen.getByRole("button", { name: "Registrar producción" }));
    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(posts()[0]).toEqual({
      ruta: "/v1/produccion/producciones",
      cuerpo: { producto: "MZP-01", toneladas: "1234.5", fecha: "2026-11-15" },
    });
  });

  test("sin mezcla o con toneladas mal escritas no se manda nada", async () => {
    montar();
    await elegir();
    expect(screen.getByRole("button", { name: "Registrar producción" })).toBeDisabled();
    await usuario.type(screen.getByLabelText("Toneladas producidas"), "2.5");
    expect(screen.getByRole("button", { name: "Registrar producción" })).toBeDisabled();
    expect(screen.getByText(/Use la coma para los decimales/)).toBeInTheDocument();
    expect(posts()).toHaveLength(0);
  });

  test("el 422 del servidor se muestra tal cual y el foco va al aviso", async () => {
    produccion = () => json({ detalle: "El material AGR-12 no existe en la arenera." }, 422);
    montar();
    await elegir();
    await usuario.type(screen.getByLabelText("Toneladas producidas"), "3");
    await usuario.click(screen.getByRole("button", { name: "Registrar producción" }));
    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("El material AGR-12 no existe en la arenera.");
    await waitFor(() => expect(alerta.closest("[tabindex]")).toBe(document.activeElement));
  });

  test("tras registrar, el aviso de éxito recibe el foco y las toneladas quedan vacías", async () => {
    montar();
    await elegir();
    await usuario.type(screen.getByLabelText("Toneladas producidas"), "2,5");
    await usuario.click(screen.getByRole("button", { name: "Registrar producción" }));
    const aviso = await screen.findByText("Producción registrada: 2,5 t de MZP-01.");
    await waitFor(() => expect(document.activeElement).toBe(aviso.closest("[tabindex]")));
    expect(screen.getByLabelText("Toneladas producidas")).toHaveValue("");
  });

  test("cambiar la fecha vuelve a buscar la receta que rige ese día", async () => {
    montar();
    await elegir();
    const fecha = screen.getByLabelText("Fecha de la producción");
    await usuario.clear(fecha);
    await usuario.type(fecha, "2026-10-01");
    await waitFor(() => {
      const nuevas = fetchFalso.mock.calls.filter((c) => String(c[0]).includes("recetas/vigente") && String(c[0]).includes("2026-10-01"));
      expect(nuevas.length).toBeGreaterThan(0);
    });
  });

  test("un 401 al leer los materiales avisa a la aplicación", async () => {
    fetchFalso.mockImplementation(async () => json({ detalle: "Sesión vencida" }, 401));
    montar();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });
});
