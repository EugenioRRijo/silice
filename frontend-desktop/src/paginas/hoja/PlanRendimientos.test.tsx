import { configure, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { PestanaPlan } from "./PestanaPlan";
import type { Resumen, VistaPlan } from "./logica";

// Tarea 21 (MP-7): «Plan desde los rendimientos» en la pestaña Plan y curva. Contrato de la ruta:
// `POST /v1/hoja/borradores/{id}/plan/rendimientos` con `{rev, cuadrillas: {codigo: "1"}, paralelas: [codigo], unidad: "dia" | "mes" |
// "semana"}` → `{rev, resumen, plan, avisos}`. Datos ficticios de la vivienda (OBRA-01 a OBRA-03); los textos de los avisos
// son los del plan («{código} tiene cantidad 0.», «{código} no tiene rendimiento: se le asignó 1 día.»).
configure({ asyncUtilTimeout: 5000 });

vi.mock("../../comun/GraficoCarbon", () => ({
  default: ({ datos }: { datos: unknown[] }) => <div data-testid="grafico" data-filas={datos.length} />,
}));

const ID = "id-borrador-vivienda-0001";
const RUTA = `/v1/hoja/borradores/${ID}/plan/rendimientos`;
const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja"],
  modo_entrega: false,
};

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const m = (texto: string) => ({ texto, exacto: texto });

function resumen(rev: number): Resumen {
  return {
    rev,
    moneda: "Bs",
    total: { texto: "1000.00", exacto: "1000" },
    cambios: 1,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
  } as Resumen;
}

// La vivienda con tres partidas, una por día (el plan que trae la versión).
function planPorDia(): VistaPlan {
  return {
    hay_plan: true,
    etiquetas: ["Dia 1", "Dia 2", "Dia 3"],
    filas: [
      { partida: "OBRA-01", valores: { "Dia 1": "1", "Dia 2": "0", "Dia 3": "0" } },
      { partida: "OBRA-02", valores: { "Dia 1": "0", "Dia 2": "1", "Dia 3": "0" } },
      { partida: "OBRA-03", valores: { "Dia 1": "0", "Dia 2": "0", "Dia 3": "1" } },
    ],
    curva: [
      { periodo: "Dia 1", monto: m("100.00"), acumulado: m("100.00"), porcentaje: m("10.00") },
      { periodo: "Dia 2", monto: m("400.00"), acumulado: m("500.00"), porcentaje: m("50.00") },
      { periodo: "Dia 3", monto: m("500.00"), acumulado: m("1000.00"), porcentaje: m("100.00") },
    ],
    moneda: "Bs",
    mensaje: null,
  };
}

// Lo que contesta el servidor tras rehacerlo en semanas.
function planPorSemana(): VistaPlan {
  return {
    ...planPorDia(),
    etiquetas: ["Semana 1", "Semana 2"],
    filas: [
      { partida: "OBRA-01", valores: { "Semana 1": "1", "Semana 2": "0" } },
      { partida: "OBRA-02", valores: { "Semana 1": "0,5", "Semana 2": "0,5" } },
      { partida: "OBRA-03", valores: { "Semana 1": "1", "Semana 2": "0" } },
    ],
    curva: [
      { periodo: "Semana 1", monto: m("700.00"), acumulado: m("700.00"), porcentaje: m("70.00") },
      { periodo: "Semana 2", monto: m("300.00"), acumulado: m("1000.00"), porcentaje: m("100.00") },
    ],
  };
}

const SIN_PLAN = "Esta versión no tiene plan de trabajo, así que no hay curva de inversión.";
const sinPlan = (): VistaPlan => ({ hay_plan: false, etiquetas: [], filas: [], curva: [], moneda: "Bs", mensaje: SIN_PLAN });

describe("Hoja: plan desde los rendimientos (Tarea 21)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alAceptar = vi.fn();
  const alExpirar = vi.fn();
  let vista: VistaPlan;
  let responder: (cuerpo: Record<string, unknown>) => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alAceptar.mockReset();
    alExpirar.mockReset();
    vista = planPorDia();
    responder = (cuerpo) => {
      vista = planPorSemana();
      return json({ rev: (cuerpo.rev as number) + 1, resumen: resumen((cuerpo.rev as number) + 1), plan: vista, avisos: [] });
    };
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      if (url === RUTA && init?.method === "POST") return responder(JSON.parse(String(init.body)) as Record<string, unknown>);
      if (url.endsWith("/vistas/plan")) return json(vista);
      return new Response(null, { status: 204 });
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  function montar(rev = 3) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: "VIV",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <PestanaPlan id={ID} rev={rev} alAusente={vi.fn()} alAceptar={alAceptar} alRecargarBorrador={vi.fn(async () => {})} alReabrir={vi.fn()} />
      </ContextoAplicacion.Provider>,
    );
  }

  const envios = () =>
    fetchFalso.mock.calls.filter(([r, init]) => String(r) === RUTA && init?.method === "POST").map(([, init]) => JSON.parse(String(init?.body)));
  const lecturas = () => fetchFalso.mock.calls.filter(([r]) => String(r).endsWith("/vistas/plan")).length;
  const boton = () => screen.getByRole("button", { name: "Plan desde los rendimientos" });

  test("envía las cuadrillas de cada partida, las que van en paralelo y la unidad, y la matriz pasa a la nueva", async () => {
    montar();
    const seccion = await screen.findByRole("region", { name: "Plan desde los rendimientos" });
    const cuadrillas = within(seccion).getByRole("textbox", { name: "Cuadrillas de OBRA-02" });
    await userEvent.clear(cuadrillas);
    await userEvent.type(cuadrillas, "2");
    await userEvent.click(within(seccion).getByRole("checkbox", { name: "OBRA-03 en paralelo con la anterior" }));
    await userEvent.click(within(seccion).getByRole("radio", { name: "Semanas (5 días hábiles)" }));
    await userEvent.click(boton());

    expect(envios()).toEqual([
      { rev: 3, cuadrillas: { "OBRA-01": "1", "OBRA-02": "2", "OBRA-03": "1" }, paralelas: ["OBRA-03"], unidad: "semana" },
    ]);
    expect(await screen.findByText("Plan hecho desde los rendimientos: 2 períodos.")).toBeInTheDocument();
    expect(alAceptar).toHaveBeenCalledWith(resumen(4));
    expect(lecturas()).toBe(2);
    // La matriz se vuelve a sembrar con el plan nuevo (no conserva la de una partida por día).
    const matriz = screen.getByRole("table", { name: "Plan de trabajo" });
    expect(within(matriz).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Partida", "Semana 1", "Semana 2"]);
    expect(screen.getByRole("textbox", { name: "Semana 1, Plan de trabajo fila 2" })).toHaveValue("0,5");
  });

  test("la primera partida no puede ir en paralelo: no tiene anterior", async () => {
    montar();
    const seccion = await screen.findByRole("region", { name: "Plan desde los rendimientos" });
    expect(within(seccion).getByRole("checkbox", { name: "OBRA-01 en paralelo con la anterior" })).toBeDisabled();
    expect(within(seccion).getByRole("checkbox", { name: "OBRA-02 en paralelo con la anterior" })).toBeEnabled();
    // Por omisión: una cuadrilla por partida, nada en paralelo, en días hábiles (el plan que trae es por día).
    expect(within(seccion).getByRole("textbox", { name: "Cuadrillas de OBRA-01" })).toHaveValue("1");
    expect(within(seccion).getByRole("radio", { name: "Días hábiles" })).toBeChecked();
  });

  test("muestra los avisos de las partidas sin rendimiento o con cantidad 0", async () => {
    responder = (cuerpo) =>
      json({
        rev: (cuerpo.rev as number) + 1,
        resumen: resumen((cuerpo.rev as number) + 1),
        plan: vista,
        avisos: ["OBRA-02 tiene cantidad 0.", "OBRA-99 no tiene rendimiento: se le asignó 1 día."],
      });
    montar();
    await screen.findByRole("region", { name: "Plan desde los rendimientos" });
    await userEvent.click(boton());
    const avisos = await screen.findByRole("status", { name: "Avisos del plan" });
    expect(within(avisos).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
      "OBRA-02 tiene cantidad 0.",
      "OBRA-99 no tiene rendimiento: se le asignó 1 día.",
    ]);
    // Una sola región viva: dentro de la de los avisos no hay otra (ni log, ni status, ni alert).
    expect(avisos.querySelectorAll('[role="log"], [role="status"], [role="alert"], [aria-live]')).toHaveLength(0);
  });

  test("un plan de un solo período lo dice en singular", async () => {
    responder = (cuerpo) => {
      vista = {
        ...planPorSemana(),
        etiquetas: ["Semana 1"],
        filas: ["OBRA-01", "OBRA-02", "OBRA-03"].map((partida) => ({ partida, valores: { "Semana 1": "1" } })),
        curva: [{ periodo: "Semana 1", monto: m("1000.00"), acumulado: m("1000.00"), porcentaje: m("100.00") }],
      };
      return json({ rev: (cuerpo.rev as number) + 1, resumen: resumen((cuerpo.rev as number) + 1), plan: vista, avisos: [] });
    };
    montar();
    await screen.findByRole("region", { name: "Plan desde los rendimientos" });
    await userEvent.click(boton());
    expect(await screen.findByText("Plan hecho desde los rendimientos: 1 período.")).toBeInTheDocument();
  });

  test("sin plan, el botón envía una cuadrilla por partida en días (ya no hay «Crear plan secuencial», baja 11)", async () => {
    vista = sinPlan();
    montar(0);
    expect(await screen.findByText(SIN_PLAN)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Crear plan secuencial/ })).toBeNull();
    await userEvent.click(boton());
    expect(envios()).toEqual([{ rev: 0, cuadrillas: {}, paralelas: [], unidad: "dia" }]);
    expect(await screen.findByRole("table", { name: "Plan de trabajo" })).toBeInTheDocument();
  });

  test("un 422 muestra el texto del servidor y no toca la matriz", async () => {
    const DETALLE = "Las cuadrillas de OBRA-02 deben ser un número entero de 1 a 99.";
    responder = () => json({ detalle: DETALLE }, 422);
    montar();
    const seccion = await screen.findByRole("region", { name: "Plan desde los rendimientos" });
    const cuadrillas = within(seccion).getByRole("textbox", { name: "Cuadrillas de OBRA-02" });
    await userEvent.clear(cuadrillas);
    await userEvent.type(cuadrillas, "1,5");
    await userEvent.click(boton());
    expect(await screen.findByText(DETALLE)).toBeInTheDocument();
    expect(alAceptar).not.toHaveBeenCalled();
    expect(screen.getByRole("textbox", { name: "Día 1, Plan de trabajo fila 1" })).toHaveValue("1");
  });

  test("un rev viejo pide recargar el borrador", async () => {
    responder = () => json({ detalle: "El borrador cambió en otra ventana: vuelva a cargarlo." }, 409);
    montar();
    await screen.findByRole("region", { name: "Plan desde los rendimientos" });
    await userEvent.click(boton());
    expect(await screen.findByText("El borrador cambió en otra ventana: vuelva a cargarlo.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Recargar el borrador" })).toBeInTheDocument();
  });

  test("la sesión vencida avisa al armazón", async () => {
    responder = () => json({ detalle: "Su sesión venció." }, 401);
    montar();
    await screen.findByRole("region", { name: "Plan desde los rendimientos" });
    await userEvent.click(boton());
    await vi.waitFor(() => expect(alExpirar).toHaveBeenCalledTimes(1));
  });

  // Ola 2 (2026-11-13): la salida del 422 de una obra de más de 10.000 días («asigne más cuadrillas a las partidas largas,
  // haga el plan desde los rendimientos por meses») se sigue en esta pantalla: sin plan ya se ven las cuadrillas.
  test("sin plan, las cuadrillas de cada partida se ponen antes de hacer el plan, y por meses", async () => {
    vista = { ...sinPlan(), partidas: ["OBRA-01", "OBRA-02"] };
    montar(0);
    const seccion = await screen.findByRole("region", { name: "Plan desde los rendimientos" });
    const cuadrillas = within(seccion).getByRole("textbox", { name: "Cuadrillas de OBRA-02" });
    await userEvent.clear(cuadrillas);
    await userEvent.type(cuadrillas, "3");
    await userEvent.click(within(seccion).getByRole("radio", { name: "Meses (20 días hábiles)" }));
    await userEvent.click(boton());
    expect(envios()).toEqual([{ rev: 0, cuadrillas: { "OBRA-01": "1", "OBRA-02": "3" }, paralelas: [], unidad: "mes" }]);
  });

  test("un plan armado por meses se muestra con su unidad, no como días", async () => {
    vista = {
      ...planPorDia(),
      etiquetas: ["Mes 1", "Mes 2"],
      filas: ["OBRA-01", "OBRA-02", "OBRA-03"].map((partida) => ({ partida, valores: { "Mes 1": "0,5", "Mes 2": "0,5" } })),
      curva: [
        { periodo: "Mes 1", monto: m("500.00"), acumulado: m("500.00"), porcentaje: m("50.00") },
        { periodo: "Mes 2", monto: m("500.00"), acumulado: m("1000.00"), porcentaje: m("100.00") },
      ],
    };
    montar();
    const seccion = await screen.findByRole("region", { name: "Plan desde los rendimientos" });
    expect(within(seccion).getByRole("radio", { name: "Meses (20 días hábiles)" })).toBeChecked();
    expect(within(seccion).getByRole("radio", { name: "Días hábiles" })).not.toBeChecked();
    const matriz = screen.getByRole("table", { name: "Plan de trabajo" });
    expect(within(matriz).getAllByRole("columnheader").map((c) => c.textContent)).toEqual(["Partida", "Mes 1", "Mes 2"]);
  });
});
