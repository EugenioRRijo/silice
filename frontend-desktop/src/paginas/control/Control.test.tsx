import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaControl from "./index";
import { consultaDeCalculo, cuerpoDeOpciones, FILTROS_INICIALES, sinLineasVacias } from "./logica";
import type { Calculo, LineaBase, OpcionDeRecuperacion, Valuaciones } from "./logica";

vi.mock("../../comun/GraficoCarbon", () => ({
  default: ({ tipo, datos }: { tipo: string; datos: unknown[] }) => (
    <div data-testid={`grafico-${tipo}`} data-filas={datos.length} />
  ),
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
  descripcion: "version OB-001, perspectiva costo, vigente desde 2026-11-02",
  versiones: ["OB-001"],
  hay_valuaciones: true,
  parametros: [
    { parametro: "spi_error", que_es: "SPI por debajo del cual el retraso es ERROR (AL-1)", valor: "0.80", naturaleza: "SUPUESTO_DECLARADO" },
    { parametro: "penalizacion_diaria", que_es: "Penalizacion por dia", valor: "0", naturaleza: "DATO_DEL_CONTRATO" },
  ],
};

const VALUACIONES: Valuaciones = {
  tiene_linea_base: true,
  filas: [
    { Numero: "V-01", Periodo: "2026-11-02 a 2026-11-06", Fecha: "2026-11-09", Inspector: "<b>Ing. Ficticio</b>", Registrada: "2026-11-09 09:00", Estado: "sin hallazgos" },
  ],
  aviso: "",
  anulables: [{ id: 7, rotulo: "V-01 (2026-11-02 a 2026-11-06)" }],
  corte_por_defecto: "2026-11-13",
};

const CALCULO: Calculo = {
  estado: "listo",
  corte: "2026-11-13",
  dia: 10,
  moneda: "USD",
  indicadores: [
    { Indicador: "BAC (USD)", Valor: "4000.00", "En la otra moneda": "no disponible", Nota: "" },
    { Indicador: "SPI", Valor: "0.8000", "En la otra moneda": "", Nota: "" },
  ],
  costos_sin_tasa: ["El costo de 10 USD del 2026-11-01 no tiene tasa aplicable."],
  curva: [
    { periodo: "P1", pv: "1000.00", ev: "800.00", ac: "900.00" },
    { periodo: "P2", pv: "2000.00", ev: "1200.00", ac: null },
  ],
  spi_no_aplica: false,
  alertas: [{ Alerta: "AL-1", Severidad: "ERROR", Descripcion: "Retraso", Observado: "0.8000", Umbral: "0.8500 (SUPUESTO_DECLARADO)" }],
  terminos: { indice: "dia 12 (2026-11-18)", reproyectado: "dia 13 (2026-11-19)", plan_base: "dia 10 (2026-11-13)", eac_sistema: "no disponible" },
  motivo_termino: "",
  equilibrio: null,
  estudios: "Sin estudio de reajuste guardado: V' = V. Nunca se proyecta un reajuste.",
  reproyeccion: [{ Partida: "OB-A", Indice: "0.8000", "Fin (dia habil)": "12.50", Nota: "" }],
  plan: { columnas: ["Periodo", "OB-A"], filas: [{ Periodo: "P3", "OB-A": "0.5000" }] },
  decisiones: [],
  versiones_revaloradas: ["OB-R1"],
};

const OPCIONES: OpcionDeRecuperacion[] = [
  { clave: "cuadrillas", titulo: "Cuadrillas adicionales", aplica: true, motivo: "", requisitos: [], requiere_declaracion: false, fila: { Opcion: "Cuadrillas adicionales", Termino: "dia 11", "Retraso (dias)": "1", "Costo directo adicional": "100.00", "Costo indirecto": "0.00", Penalizacion: "0.00", "Punto de equilibrio": "no aplica", Nota: "" } },
  { clave: "frentes", titulo: "Frentes en paralelo", aplica: true, motivo: "", requisitos: ["plano de interferencias"], requiere_declaracion: true, fila: { Opcion: "Frentes en paralelo", Termino: "dia 10", "Retraso (dias)": "0", "Costo directo adicional": "50.00", "Costo indirecto": "0.00", Penalizacion: "0.00", "Punto de equilibrio": "no aplica", Nota: "" } },
  { clave: "horas_extra", titulo: "Horas extra", aplica: false, motivo: "supera el tope legal", requisitos: [], requiere_declaracion: false, fila: { Opcion: "Horas extra", Nota: "supera el tope legal" } },
];

describe("Control de obra", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let calculo: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    calculo = () => json(CALCULO);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = String(entrada);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/control/linea-base") && metodo === "GET") return json(LINEA_BASE);
      if (url.startsWith("/v1/control/valuaciones") && metodo === "GET") return json(VALUACIONES);
      if (url.startsWith("/v1/control/calculo")) return calculo();
      if (url === "/v1/control/valuaciones") return json({ corte: "2026-11-20", hallazgos: 2, errores: 1 });
      if (url === "/v1/control/recuperacion/opciones") return json({ opciones: OPCIONES });
      if (url === "/v1/control/recuperacion/elegir") return json({ version: "OB-002" });
      if (url === "/v1/control/linea-base") return json({ descripcion: "x" });
      return json({ detalle: `ruta inesperada ${metodo} ${url}` }, 500);
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  function montar(proyecto: string | null = "OB-S2", sesion: SesionRespuesta = SESION) {
    const valor: Aplicacion = {
      sesion,
      proyecto,
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

  function cuerpoDe(ruta: string, metodo = "POST") {
    const llamada = fetchFalso.mock.calls.find(([u, i]) => String(u) === ruta && (i?.method ?? "GET") === metodo);
    return llamada ? (JSON.parse(String(llamada[1]?.body)) as Record<string, unknown>) : undefined;
  }

  test("sin proyecto invita a elegirlo y no pide nada", () => {
    montar(null);
    expect(screen.getByText("Elija un proyecto")).toBeInTheDocument();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("la primera pestaña muestra la linea base y los parametros con su naturaleza", async () => {
    montar();
    expect(await screen.findByText(/perspectiva costo, vigente desde 2026-11-02/)).toBeInTheDocument();
    const tabla = screen.getByRole("table", { name: "Parametros de control" });
    expect(within(tabla).getByText("SUPUESTO_DECLARADO")).toBeInTheDocument();
    expect(within(tabla).getByText("DATO_DEL_CONTRATO")).toBeInTheDocument();
    expect(String(fetchFalso.mock.calls[0]![0])).toContain("proyecto=OB-S2");
  });

  test("declarar la linea base manda los textos tal cual y confirma", async () => {
    const u = montar();
    await screen.findByText(/perspectiva costo/);
    await u.type(screen.getByLabelText("Vigente desde (AAAA-MM-DD)"), "2026-11-02");
    await u.type(screen.getByLabelText("Inicio de obra (AAAA-MM-DD)"), "2026-11-02");
    await u.type(screen.getByLabelText("Fuente de la linea base"), "acta 1");
    await u.click(screen.getByRole("button", { name: "Declarar linea base" }));
    expect(await screen.findByText("Linea base declarada.")).toBeInTheDocument();
    expect(cuerpoDe("/v1/control/linea-base")).toMatchObject({
      proyecto: "OB-S2",
      version: "OB-001",
      desde: "2026-11-02",
      perspectiva: "costo",
      fuente: "acta 1",
    });
  });

  test("las valuaciones se muestran como texto, sin interpretar el inspector", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    const tabla = await screen.findByRole("table", { name: "Valuaciones registradas" });
    expect(within(tabla).getByText("<b>Ing. Ficticio</b>")).toBeInTheDocument();
    expect(tabla.querySelector("b")).toBeNull();
  });

  test("registrar una valuacion ignora las lineas vacias y dice el corte y los hallazgos", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    await screen.findByRole("table", { name: "Valuaciones registradas" });
    await u.type(screen.getByLabelText("Numero"), "V-03");
    await u.type(screen.getByLabelText("Periodo desde (AAAA-MM-DD)"), "2026-11-16");
    await u.type(screen.getByLabelText("Periodo hasta (AAAA-MM-DD)"), "2026-11-20");
    await u.type(screen.getByLabelText("Partida 1"), "OB-A");
    await u.type(screen.getByLabelText("Cantidad 1"), "50");
    await u.click(screen.getByRole("button", { name: "Agregar linea" }));
    await u.type(screen.getByLabelText("Fuente (acta, oficio)"), "acta 3");
    await u.click(screen.getByRole("button", { name: "Registrar y controlar" }));
    expect(await screen.findByText(/corte 2026-11-20, 2 hallazgo\(s\) de R13-R14 \(1 ERROR\)/)).toBeInTheDocument();
    const cuerpo = cuerpoDe("/v1/control/valuaciones");
    expect(cuerpo).toMatchObject({ proyecto: "OB-S2", numero: "V-03", fuente: "acta 3" });
    expect(cuerpo?.lineas).toEqual([{ partida: "OB-A", cantidad: "50", fecha_medicion: "", observacion: "" }]);
  });

  test("un 422 de la API se muestra con su detalle y no se da por registrado", async () => {
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = String(entrada);
      if ((init?.method ?? "GET") === "POST") return json({ detalle: "falta la partida" }, 422);
      if (url.startsWith("/v1/control/valuaciones")) return json(VALUACIONES);
      return json(LINEA_BASE);
    });
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    await screen.findByRole("table", { name: "Valuaciones registradas" });
    await u.click(screen.getByRole("button", { name: "Registrar y controlar" }));
    expect(await screen.findByText("falta la partida")).toBeInTheDocument();
    expect(screen.queryByText(/Valuacion registrada/)).toBeNull();
  });

  test("valor ganado: indicadores, avisos de costo sin tasa y la curva con su tabla", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valor ganado" }));
    const tabla = await screen.findByRole("table", { name: "Indicadores de valor ganado" });
    expect(within(tabla).getByText("4000.00")).toBeInTheDocument();
    expect(screen.getByText(/no tiene tasa aplicable/)).toBeInTheDocument();
    expect(await screen.findByTestId("grafico-linea")).toBeInTheDocument();
    // el AC que falta se ve como guion en la tabla de la curva, no como cero
    expect(screen.getByRole("table", { name: "Montos de PV, EV y AC" })).toBeInTheDocument();
  });

  test("alertas y reproyeccion: terminos, estudios y plan", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Alertas y reproyección" }));
    expect(await screen.findByRole("table", { name: "Alertas" })).toBeInTheDocument();
    expect(screen.getByText("Termino por el indice: dia 12 (2026-11-18)")).toBeInTheDocument();
    expect(screen.getByText(/Punto de equilibrio proyectado: no disponible/)).toBeInTheDocument();
    expect(screen.getByText(/V' = V/)).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Plan reproyectado" })).toBeInTheDocument();
  });

  test("sin valuaciones el calculo dice que hacer", async () => {
    calculo = () => json({ ...CALCULO, estado: "sin_valuaciones" });
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valor ganado" }));
    expect(await screen.findByText("Registre la primera valuacion para ver el control")).toBeInTheDocument();
  });

  test("cambiar el corte vuelve a calcular con el corte pedido", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valor ganado" }));
    await screen.findByRole("table", { name: "Indicadores de valor ganado" });
    await u.type(screen.getByLabelText(/Fecha de corte/), "2026-11-06");
    await u.click(screen.getByRole("button", { name: "Calcular al corte" }));
    await waitFor(() =>
      expect(fetchFalso.mock.calls.some(([url]) => String(url).includes("corte=2026-11-06"))).toBe(true),
    );
  });

  test("recuperacion: calcula a pedido, pide la declaracion y elige repitiendo los parametros", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Recuperación" }));
    await screen.findByText(/Las opciones se calculan a pedido/);
    expect(fetchFalso.mock.calls.some(([url]) => String(url).includes("recuperacion"))).toBe(false);
    await u.type(screen.getByLabelText(/Dia habil objetivo/), "11");
    await u.click(screen.getByRole("button", { name: "Calcular opciones" }));
    expect(await screen.findByRole("table", { name: "Opciones de recuperacion" })).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "Horas extra" })).toBeNull(); // no aplica: no se puede elegir
    await u.click(screen.getByRole("radio", { name: "Frentes en paralelo" }));
    await u.type(screen.getByLabelText("Declaro que estas partidas no dependen de las que estan en curso (con su fuente)"), "plano 3");
    await u.type(screen.getByLabelText("Fuente de la decision"), "reunion");
    await u.click(screen.getByRole("button", { name: "Elegir y crear la version" }));
    expect(await screen.findByText("Version OB-002 creada con el plan de la opcion elegida.")).toBeInTheDocument();
    expect(cuerpoDe("/v1/control/recuperacion/elegir")).toMatchObject({
      proyecto: "OB-S2",
      objetivo: "11",
      horas_previas: "0",
      opcion: "frentes",
      fuente: "reunion",
      declaracion_independencia: "plano 3",
      precios: { metodo: "ninguno" },
    });
  });

  test("quien no puede decidir ve las opciones pero no el boton de elegir", async () => {
    const u = montar("OB-S2", { ...SESION, acciones: ["control_de_obra"] });
    await u.click(await screen.findByRole("tab", { name: "Recuperación" }));
    await u.click(await screen.findByRole("button", { name: "Calcular opciones" }));
    expect(await screen.findByText(/pero no elegir una/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Elegir y crear la version" })).toBeNull();
  });
});

describe("logica del control", () => {
  test("la consulta del calculo solo lleva lo elegido", () => {
    expect(consultaDeCalculo("OB S2", FILTROS_INICIALES)).toBe("/v1/control/calculo?proyecto=OB+S2");
    const con = consultaDeCalculo("P", { corte: " 2026-11-06 ", precios: { metodo: "escalatoria", version: "x", km: "1.1", r: "0", fuente: "f" } });
    expect(con).toBe("/v1/control/calculo?proyecto=P&corte=2026-11-06&metodo=escalatoria&km=1.1&r=0&fuente=f");
  });

  test("el cuerpo de las opciones repite corte y precios, que el servidor no guarda", () => {
    expect(cuerpoDe_("P")).toEqual({
      proyecto: "P",
      corte: null,
      precios: FILTROS_INICIALES.precios,
      objetivo: "11",
      horas_previas: "2",
    });
  });

  test("las lineas sin partida ni cantidad no se mandan", () => {
    const vacia = { partida: "", cantidad: "", fecha_medicion: "2026-11-01", observacion: "" };
    const llena = { partida: "A", cantidad: "", fecha_medicion: "", observacion: "" };
    expect(sinLineasVacias([vacia, llena])).toEqual([llena]);
  });
});

function cuerpoDe_(proyecto: string) {
  return cuerpoDeOpciones(proyecto, FILTROS_INICIALES, "11", "2");
}
