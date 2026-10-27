// MP-7, Tarea 22: la causa del retraso por linea de valuacion y la tabla «Atraso por partida».
// La lista de causas y los textos de cada atraso los da la API (`GET /v1/control/valuaciones` y `GET /v1/control/calculo`):
// la pantalla los muestra tal cual y solo pone los dias en es-VE. Oraculos escritos a mano.
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaControl from "./index";
import { LINEA_VACIA, lineaParaApi } from "./logica";
import type { Calculo, LineaBase, Valuaciones } from "./logica";

vi.mock("../../comun/GraficoCarbon", () => ({
  default: () => <div data-testid="grafico" />,
}));

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["control_de_obra", "decidir_recuperacion"],
  modo_entrega: false,
};

const LINEA_BASE: LineaBase = {
  tiene_linea_base: true,
  descripcion: "versión DOS-001, perspectiva costo, vigente desde 02/11/2026",
  versiones: ["DOS-001"],
  hay_valuaciones: false,
  parametros: [],
};

const CAUSAS = [
  { clave: "compra_tardia", nombre: "Compra tardía" },
  { clave: "precio", nombre: "Precio" },
  { clave: "clima", nombre: "Lluvia o clima" },
  { clave: "cambio_cliente", nombre: "Cambio del cliente" },
  { clave: "falta_personal", nombre: "Falta de personal" },
  { clave: "falla_equipo", nombre: "Falla de equipo" },
  { clave: "otra", nombre: "Otra" },
];

const VALUACIONES: Valuaciones = {
  tiene_linea_base: true,
  filas: [],
  aviso: "",
  anulables: [],
  corte_por_defecto: "2026-11-06",
  causas: CAUSAS,
};

const ATRASOS = [
  { codigo: "A", dias: 5, causa: "compra_tardia", texto: "A atrasada 5 días: Compra tardía" },
  { codigo: "OBRA-05", dias: 1200, causa: null, texto: "OBRA-05 atrasada 1.200 días: sin causa declarada" },
];

function calculo(atrasos: Calculo["atrasos"]): Calculo {
  return {
    estado: "listo",
    corte: "2026-11-06",
    dia: 5,
    moneda: "Bs",
    indicadores: [],
    costos_sin_tasa: [],
    curva: [],
    spi_no_aplica: false,
    alertas: [],
    terminos: { indice: "día 10 (13/11/2026)", reproyectado: "día 10 (13/11/2026)", plan_base: "día 7 (10/11/2026)", eac_sistema: "no disponible" },
    motivo_termino: "",
    equilibrio: null,
    estudios: "Sin estudio de reajuste guardado: V' = V. Nunca se proyecta un reajuste.",
    reproyeccion: [],
    plan: null,
    decisiones: [],
    versiones_revaloradas: [],
    atrasos,
    precios_convertidos: [],
  };
}

describe("Control de obra: causas de retraso y atraso por partida", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let respuestaCalculo: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    respuestaCalculo = () => json(calculo(ATRASOS));
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = String(entrada);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/control/linea-base") && metodo === "GET") return json(LINEA_BASE);
      if (url.startsWith("/v1/control/valuaciones") && metodo === "GET") return json(VALUACIONES);
      if (url.startsWith("/v1/control/calculo")) return respuestaCalculo();
      if (url === "/v1/control/valuaciones") return json({ corte: "2026-11-06", hallazgos: 0, errores: 0 });
      return json({ detalle: `ruta inesperada ${metodo} ${url}` }, 500);
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  function montar() {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: "Obra de dos partidas",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    render(
      <ContextoAplicacion.Provider value={valor}>
        <PaginaControl />
      </ContextoAplicacion.Provider>,
    );
    return userEvent.setup();
  }

  function lineasEnviadas() {
    const llamada = fetchFalso.mock.calls.find(([u, i]) => String(u) === "/v1/control/valuaciones" && i?.method === "POST");
    expect(llamada).toBeDefined();
    return (JSON.parse(String(llamada![1]?.body)) as { lineas: unknown[] }).lineas;
  }

  async function abrirValuaciones(u: ReturnType<typeof userEvent.setup>) {
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    return screen.findByRole("combobox", { name: "Causa del retraso 1" });
  }

  test("cada linea tiene su selector de causa con «Sin causa» y las causas de la API, por su nombre", async () => {
    const u = montar();
    const selector = await abrirValuaciones(u);
    const opciones = within(selector).getAllByRole("option").map((o) => o.textContent);
    expect(opciones).toEqual([
      "Sin causa",
      "Compra tardía",
      "Precio",
      "Lluvia o clima",
      "Cambio del cliente",
      "Falta de personal",
      "Falla de equipo",
      "Otra",
    ]);
    expect(selector).toHaveValue("");
    await u.click(screen.getByRole("button", { name: "Agregar línea" }));
    expect(screen.getByRole("combobox", { name: "Causa del retraso 2" })).toHaveValue("");
  });

  test("la causa elegida viaja con su linea y una linea sin causa la manda nula", async () => {
    const u = montar();
    const selector = await abrirValuaciones(u);
    await u.type(screen.getByLabelText("Partida 1"), "A");
    await u.type(screen.getByLabelText("Cantidad 1"), "5");
    await u.selectOptions(selector, "Compra tardía");
    await u.click(screen.getByRole("button", { name: "Agregar línea" }));
    await u.type(screen.getByLabelText("Partida 2"), "B");
    await u.type(screen.getByLabelText("Cantidad 2"), "1,5");
    await u.click(screen.getByRole("button", { name: "Registrar y controlar" }));
    await screen.findByText(/Valuación registrada/);
    expect(lineasEnviadas()).toEqual([
      { partida: "A", cantidad: "5", fecha_medicion: "", observacion: "", causa: "compra_tardia" },
      { partida: "B", cantidad: "1.5", fecha_medicion: "", observacion: "", causa: null },
    ]);
  });

  test("lineaParaApi lee la cantidad con coma y deja la causa vacia como nula", () => {
    expect(lineaParaApi({ ...LINEA_VACIA, partida: "A", cantidad: "1.234,5" })).toEqual({
      partida: "A",
      cantidad: "1234.5",
      fecha_medicion: "",
      observacion: "",
      causa: null,
    });
    expect(lineaParaApi({ ...LINEA_VACIA, partida: "A", cantidad: "5", causa: "clima" }).causa).toBe("clima");
  });

  test("«Atraso por partida» pinta el texto de cada atraso y los dias en es-VE", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Alertas y reproyección" }));
    expect(await screen.findByRole("heading", { level: 2, name: "Atraso por partida" })).toBeInTheDocument();
    const tabla = screen.getByRole("table", { name: "Atraso por partida" });
    const encabezados = within(tabla).getAllByRole("columnheader").map((c) => c.textContent);
    expect(encabezados).toEqual(["Partida", "Días de atraso", "Qué pasa"]);
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(filas.map((f) => within(f).getAllByRole("cell").map((c) => c.textContent))).toEqual([
      ["A", "5", "A atrasada 5 días: Compra tardía"],
      ["OBRA-05", "1.200", "OBRA-05 atrasada 1.200 días: sin causa declarada"],
    ]);
  });

  test("sin atrasos lo dice en vez de una tabla vacia", async () => {
    respuestaCalculo = () => json(calculo([]));
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Alertas y reproyección" }));
    expect(await screen.findByText("Ninguna partida va atrasada contra su plan.")).toBeInTheDocument();
    expect(screen.queryByRole("table", { name: "Atraso por partida" })).toBeNull();
  });
});
