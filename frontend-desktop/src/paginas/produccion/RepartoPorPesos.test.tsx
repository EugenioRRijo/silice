import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import CostoPorTonelada from "./CostoPorTonelada";

// Datos ficticios. La cantera se reparte por tonelada salvo que la persona pida pesos; la pantalla solo manda los
// porcentajes como fracciones («75 %» -> «0.75») y bloquea Calcular si no suman 100 %: el reparto lo hace el servidor.
const ANA: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["operar_arenera", "registrar_costos_produccion"],
  modo_entrega: false,
};
const CALCULO = {
  id: 9,
  periodo: "2026-11",
  moneda: "Bs",
  huella: "c".repeat(64),
  usuario: "ana",
  registrado: "2026-11-30T10:00:00",
  productos: [{ codigo: "AGR-12", por_tonelada: "5", presentado: "5.00" }],
  instantanea: { entradas: { agregados: ["AGR-12", "AGR-19"], producido: {} }, resultado: { total_cantera: "750", total_planta: "0" } },
  publicado: null,
};

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

describe("Reparto de la cantera por pesos", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let usuario: ReturnType<typeof userEvent.setup>;

  const posts = () =>
    fetchFalso.mock.calls
      .filter((c) => c[1]?.method === "POST")
      .map((c) => ({ ruta: String(c[0]), cuerpo: c[1]?.body ? JSON.parse(String(c[1].body)) : null }));

  async function montarYElegirMoneda() {
    render(
      <ContextoAplicacion.Provider value={{ sesion: ANA, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() }}>
        <MemoryRouter>
          <CostoPorTonelada />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
    await screen.findByText(/AGR-12: 150 t/);
    await usuario.selectOptions(screen.getByLabelText("Moneda del cálculo"), "Bs");
  }

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 11, 15, 10, 0, 0));
    usuario = userEvent.setup();
    fijarCsrf("tok");
    fetchFalso.mockReset();
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      const metodo = init?.method ?? "GET";
      if (url.pathname === "/v1/produccion/producido") {
        if (url.searchParams.get("periodo") === "2026-10") return json([]); // un mes sin producción
        return json([
          { codigo: "AGR-12", toneladas: "150" },
          { codigo: "AGR-19", toneladas: "50" },
          { codigo: "MZP-01", toneladas: "100" },
        ]);
      }
      if (url.pathname === "/v1/produccion/recetas/vigentes") {
        return json([{ id: 1, producto: "MZP-01", componentes: [], fuente: "f", vigente_desde: "2026-01-01" }]);
      }
      if (url.pathname === "/v1/produccion/recetas/vigente") {
        return url.searchParams.get("producto") === "MZP-01"
          ? json({ id: 1, producto: "MZP-01", componentes: [], fuente: "f", vigente_desde: "2026-01-01" })
          : json({ detalle: "No hay receta vigente." }, 404);
      }
      if (url.pathname === "/v1/produccion/calculos" && metodo === "POST") return json(CALCULO, 201);
      if (url.pathname === "/v1/produccion/calculos") return json([]);
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  test("con la casilla apagada no se mandan pesos", async () => {
    await montarYElegirMoneda();
    expect(screen.getByRole("checkbox", { name: "Repartir la cantera por pesos" })).not.toBeChecked();
    await usuario.click(screen.getByRole("button", { name: "Calcular costo por tonelada" }));
    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(posts()[0]!.cuerpo).toEqual({ periodo: "2026-11", moneda: "Bs" });
  });

  test("un campo de porcentaje por agregado producido, y ninguno para las mezclas", async () => {
    await montarYElegirMoneda();
    await usuario.click(screen.getByRole("checkbox", { name: "Repartir la cantera por pesos" }));
    expect(await screen.findByLabelText("Porcentaje de AGR-12")).toBeInTheDocument();
    expect(screen.getByLabelText("Porcentaje de AGR-19")).toBeInTheDocument();
    expect(screen.queryByLabelText("Porcentaje de MZP-01")).not.toBeInTheDocument();
  });

  test("Calcular se bloquea si los porcentajes no suman 100 % y dice cuánto suman", async () => {
    await montarYElegirMoneda();
    await usuario.click(screen.getByRole("checkbox", { name: "Repartir la cantera por pesos" }));
    await usuario.type(await screen.findByLabelText("Porcentaje de AGR-12"), "70");
    await usuario.type(screen.getByLabelText("Porcentaje de AGR-19"), "20,5");
    expect(screen.getByText("Los porcentajes suman 90,5 % y deben sumar 100 %.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Calcular costo por tonelada" })).toBeDisabled();
    expect(posts()).toHaveLength(0);
  });

  test("75 % y 25 % se mandan como «0.75» y «0.25»", async () => {
    await montarYElegirMoneda();
    await usuario.click(screen.getByRole("checkbox", { name: "Repartir la cantera por pesos" }));
    await usuario.type(await screen.findByLabelText("Porcentaje de AGR-12"), "75");
    await usuario.type(screen.getByLabelText("Porcentaje de AGR-19"), "25");
    const boton = screen.getByRole("button", { name: "Calcular costo por tonelada" });
    expect(boton).toBeEnabled();
    await usuario.click(boton);
    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(posts()[0]!.cuerpo).toEqual({ periodo: "2026-11", moneda: "Bs", pesos: { "AGR-12": "0.75", "AGR-19": "0.25" } });
  });

  test("apagar la casilla vuelve a mandar sin pesos", async () => {
    await montarYElegirMoneda();
    const casilla = screen.getByRole("checkbox", { name: "Repartir la cantera por pesos" });
    await usuario.click(casilla);
    await usuario.type(await screen.findByLabelText("Porcentaje de AGR-12"), "75");
    await usuario.click(casilla);
    await usuario.click(screen.getByRole("button", { name: "Calcular costo por tonelada" }));
    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(posts()[0]!.cuerpo).toEqual({ periodo: "2026-11", moneda: "Bs" });
  });

  test("un porcentaje mal escrito se dice junto al campo", async () => {
    await montarYElegirMoneda();
    await usuario.click(screen.getByRole("checkbox", { name: "Repartir la cantera por pesos" }));
    await usuario.type(await screen.findByLabelText("Porcentaje de AGR-12"), "7.5");
    expect(screen.getByText(/Use la coma para los decimales/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Calcular costo por tonelada" })).toBeDisabled();
  });

  async function cambiarMes(mes: string) {
    fireEvent.change(screen.getByLabelText("Mes"), { target: { value: mes } });
    await screen.findByText(mes === "2026-10" ? "Todavía no hay producción registrada en este mes." : /AGR-12: 150 t/);
  }

  test("con porcentajes a medias, cambiar a un mes sin producción deja Calcular habilitado y sin pesos", async () => {
    await montarYElegirMoneda();
    await usuario.click(screen.getByRole("checkbox", { name: "Repartir la cantera por pesos" }));
    await usuario.type(await screen.findByLabelText("Porcentaje de AGR-12"), "70");
    await cambiarMes("2026-10");
    const boton = screen.getByRole("button", { name: "Calcular costo por tonelada" });
    expect(boton).toBeEnabled();
    await usuario.click(boton);
    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(posts()[0]!.cuerpo).toEqual({ periodo: "2026-10", moneda: "Bs" });
  });

  test("con un reparto válido, cambiar de mes apaga la casilla y no manda los pesos del mes anterior", async () => {
    await montarYElegirMoneda();
    await usuario.click(screen.getByRole("checkbox", { name: "Repartir la cantera por pesos" }));
    await usuario.type(await screen.findByLabelText("Porcentaje de AGR-12"), "75");
    await usuario.type(screen.getByLabelText("Porcentaje de AGR-19"), "25");
    fireEvent.change(screen.getByLabelText("Mes"), { target: { value: "2026-09" } });
    await waitFor(() => expect(screen.getByRole("checkbox", { name: "Repartir la cantera por pesos" })).not.toBeChecked());
    await usuario.click(screen.getByRole("button", { name: "Calcular costo por tonelada" }));
    await waitFor(() => expect(posts()).toHaveLength(1));
    expect(posts()[0]!.cuerpo).toEqual({ periodo: "2026-09", moneda: "Bs" });
  });

  test("un porcentaje en cero o vacío bloquea Calcular y nombra el agregado", async () => {
    await montarYElegirMoneda();
    await usuario.click(screen.getByRole("checkbox", { name: "Repartir la cantera por pesos" }));
    await usuario.type(await screen.findByLabelText("Porcentaje de AGR-12"), "100");
    await usuario.type(screen.getByLabelText("Porcentaje de AGR-19"), "0");
    expect(screen.getByRole("button", { name: "Calcular costo por tonelada" })).toBeDisabled();
    expect(screen.getByText("El porcentaje de AGR-19 debe ser mayor que cero.")).toBeInTheDocument();
    await usuario.clear(screen.getByLabelText("Porcentaje de AGR-19"));
    expect(screen.getByText(/Falta el porcentaje de AGR-19./)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Calcular costo por tonelada" })).toBeDisabled();
  });

  test("pide las recetas vigentes en una sola petición y nunca consulta la receta por producto", async () => {
    await montarYElegirMoneda();
    await usuario.click(screen.getByRole("checkbox", { name: "Repartir la cantera por pesos" }));
    expect(await screen.findByLabelText("Porcentaje de AGR-12")).toBeInTheDocument();
    expect(screen.getByLabelText("Porcentaje de AGR-19")).toBeInTheDocument();

    const campos = screen.getAllByLabelText(/^Porcentaje de/).map((c) => c.getAttribute("id"));
    expect(campos).toEqual(["reparto-AGR-12", "reparto-AGR-19"]);

    const llamadasVigentes = fetchFalso.mock.calls
      .map((c) => String(c[0]))
      .filter((r) => r.startsWith("/v1/produccion/recetas/vigentes"));
    const llamadasVigente = fetchFalso.mock.calls
      .map((c) => String(c[0]))
      .filter((r) => r.startsWith("/v1/produccion/recetas/vigente?") || r === "/v1/produccion/recetas/vigente");

    expect(llamadasVigentes).toEqual(["/v1/produccion/recetas/vigentes?fecha=2026-11-30"]);
    expect(llamadasVigente).toEqual([]);
  });
});
