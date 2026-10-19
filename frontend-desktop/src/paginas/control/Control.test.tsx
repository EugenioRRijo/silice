import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ErrorDeApi } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaControl from "./index";
import { TITULOS_VISIBLES, columnasDe, consultaDeCalculo, errorDeCarga, etiquetaDeCodigo, textoLlano, cuerpoDeOpciones, FILTROS_INICIALES, sinLineasVacias } from "./logica";
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

  test("un 404 del calculo muestra el detalle de la API y nunca el codigo crudo no_disponible (V-12)", async () => {
    calculo = () => json({ detalle: "El proyecto «OB-S2» no existe en este caso." }, 404);
    const usuario = montar();
    await usuario.click(await screen.findByRole("tab", { name: "Valor ganado" }));
    expect(await screen.findByText("El proyecto «OB-S2» no existe en este caso.")).toBeInTheDocument();
    expect(screen.queryByText("no_disponible")).not.toBeInTheDocument();
  });

  test("errorDeCarga traduce los estados sin detalle a una frase y conserva el detalle si existe", () => {
    expect(errorDeCarga({ estado: "no_disponible", error: new Error("x") })).toBe("No se encontró lo pedido.");
    expect(errorDeCarga({ estado: "sin_permiso", error: null })).toBe("Su cuenta no tiene permiso para ver esto.");
    const conDetalle = new ErrorDeApi(404, "No hay línea base.");
    expect(errorDeCarga({ estado: "no_disponible", error: conDetalle })).toBe(conDetalle);
    expect(errorDeCarga({ estado: "error", error: "falla" })).toBe("falla");
    expect(errorDeCarga({ estado: "cargando" })).toBeNull();
  });

  test("los titulos de columna de la API se leen con tilde y la clave sigue siendo la original (V-20)", () => {
    const [numero, periodo, indice, fin] = columnasDe(["Numero", "Periodo", "Indice", "Fin (dia habil)"]);
    expect([numero!.titulo, periodo!.titulo, indice!.titulo, fin!.titulo]).toEqual([
      "Número",
      "Período",
      "Índice",
      "Fin (día hábil)",
    ]);
    expect([numero!.clave, indice!.clave, fin!.clave]).toEqual(["Numero", "Indice", "Fin (dia habil)"]);
    expect(columnasDe(["Columna nueva"])[0]!.titulo).toBe("Columna nueva");
    expect(TITULOS_VISIBLES["Retraso (dias)"]).toBe("Retraso (días)");
  });

  test("las cifras de las tablas de resultados se leen en es-VE y el exacto queda en el title", () => {
    const [, valor] = columnasDe(["Indicador", "Valor"], ["Valor"]);
    expect(valor!.presentar!("4358.20")).toBe("4.358,20");
    expect(valor!.presentar!("no disponible")).toBe("no disponible");
    expect(valor!.numerica).toBe(true);
  });

  test("las fechas de los formularios usan el selector de fecha y no piden escribir AAAA-MM-DD", async () => {
    const u = montar();
    await screen.findByText(/perspectiva costo/);
    expect(screen.getByLabelText("Vigente desde")).toHaveAttribute("type", "date");
    expect(screen.getByLabelText("Inicio de obra")).toHaveAttribute("type", "date");
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    await screen.findByRole("table", { name: "Valuaciones registradas" });
    for (const nombre of ["Período desde", "Período hasta", "Fecha de la valuación"]) {
      expect(screen.getByLabelText(nombre)).toHaveAttribute("type", "date");
    }
    expect(document.body.textContent).not.toContain("AAAA-MM-DD");
  });

  test("las tablas de valuaciones muestran los encabezados con tilde (V-20)", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    const tabla = await screen.findByRole("table", { name: "Valuaciones registradas" });
    expect(within(tabla).getByRole("columnheader", { name: "Número" })).toBeInTheDocument();
  });

  test("cada codigo interno tiene su etiqueta en español y los desconocidos se muestran tal cual (V-22)", () => {
    const esperadas: Record<string, string> = {
      spi_error: "Umbral de SPI para error",
      cpi_error: "Umbral de CPI para error",
      retraso_error: "Retraso del término para error",
      precio_info: "Desvío de precio que avisa",
      equilibrio_puntos: "Subida del punto de equilibrio que advierte",
      eta_cuadrilla: "Eficiencia de la cuadrilla adicional",
      cuadrillas_max: "Cuadrillas máximas por frente",
      eta_horas_extra: "Eficiencia de la hora extra",
      horas_extra_dia: "Horas extra por día",
      recargo_horas_extra: "Recargo de las horas extra",
      fcas_en_horas_extra: "FCAS sobre las horas extra",
      penalizacion_diaria: "Penalización diaria por retraso",
      fuente_penalizacion: "Fuente de la penalización",
      SUPUESTO_DECLARADO: "Supuesto declarado",
      DATO_DEL_CONTRATO: "Dato del contrato",
      "AL-1": "Retraso (SPI)",
      "AL-2": "Sobrecosto (CPI)",
      "AL-3": "Retraso del término",
      "AL-4": "Punto de equilibrio",
      "AL-5": "Desvío de precio",
      "AL-6": "Partida detenida",
    };
    for (const [codigo, etiqueta] of Object.entries(esperadas)) expect(etiquetaDeCodigo(codigo)).toBe(etiqueta);
    expect(etiquetaDeCodigo("CODIGO_NUEVO")).toBe("CODIGO_NUEVO");
  });

  test("textoLlano traduce los codigos metidos en un texto y quita los parentesis tecnicos (V-22)", () => {
    expect(textoLlano("SPI por debajo del cual el retraso es ERROR (AL-1)")).toBe("SPI por debajo del cual el retraso es ERROR");
    expect(textoLlano("Eficiencia de cada cuadrilla adicional (eta)")).toBe("Eficiencia de cada cuadrilla adicional");
    expect(textoLlano("Eficiencia de la hora extra (eta_he)")).toBe("Eficiencia de la hora extra");
    expect(textoLlano("0.8500 (SUPUESTO_DECLARADO)")).toBe("0.8500 (supuesto declarado)");
    expect(textoLlano("0.5 (DATO_DEL_CONTRATO)")).toBe("0.5 (dato del contrato)");
    expect(textoLlano("texto sin codigos")).toBe("texto sin codigos");
  });

  test("sin proyecto invita a elegirlo y no pide nada", () => {
    montar(null);
    expect(screen.getByText("Elija un proyecto")).toBeInTheDocument();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("la primera pestaña muestra la linea base y los parametros con su naturaleza", async () => {
    montar();
    expect(await screen.findByText(/perspectiva costo, vigente desde 2026-11-02/)).toBeInTheDocument();
    const tabla = screen.getByRole("table", { name: "Parámetros de control" });
    // V-22: la naturaleza y el parametro se leen en español; el codigo queda en el title
    expect(within(tabla).getAllByText("Supuesto declarado")[0]).toHaveAttribute("title", "SUPUESTO_DECLARADO");
    expect(within(tabla).getByText("Dato del contrato")).toHaveAttribute("title", "DATO_DEL_CONTRATO");
    expect(within(tabla).getByText("Umbral de SPI para error")).toHaveAttribute("title", "spi_error");
    expect(within(tabla).queryByText("spi_error")).toBeNull();
    expect(within(tabla).queryByText(/AL-1/)).toBeNull();
    expect(String(fetchFalso.mock.calls[0]![0])).toContain("proyecto=OB-S2");
  });

  test("declarar la linea base manda los textos tal cual y confirma", async () => {
    const u = montar();
    await screen.findByText(/perspectiva costo/);
    await u.type(screen.getByLabelText("Vigente desde"), "2026-11-02");
    await u.type(screen.getByLabelText("Inicio de obra"), "2026-11-02");
    await u.type(screen.getByLabelText("Fuente de la línea base"), "acta 1");
    await u.click(screen.getByRole("button", { name: "Declarar línea base" }));
    expect(await screen.findByText("Línea base declarada.")).toBeInTheDocument();
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
    await u.type(screen.getByLabelText("Número"), "V-03");
    await u.type(screen.getByLabelText("Período desde"), "2026-11-16");
    await u.type(screen.getByLabelText("Período hasta"), "2026-11-20");
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
    expect(within(tabla).getByText("4.000,00")).toHaveAttribute("title", "4000.00");
    expect(within(tabla).queryByText("4000.00")).toBeNull();
    expect(within(tabla).getByText("4.000,00").closest("td")).toHaveClass("silice-cifra");
    expect(screen.getByText(/no tiene tasa aplicable/)).toBeInTheDocument();
    expect(await screen.findByTestId("grafico-linea")).toBeInTheDocument();
    // el AC que falta se ve como guion en la tabla de la curva, no como cero
    const montos = screen.getByRole("table", { name: "Montos de PV, EV y AC" });
    expect(within(montos).getByRole("columnheader", { name: "Período" })).toBeInTheDocument();
    expect(within(montos).getByText("1.000,00")).toHaveAttribute("title", "1000.00");
  });

  test("alertas y reproyeccion: terminos, estudios y plan", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Alertas y reproyección" }));
    const alertas = await screen.findByRole("table", { name: "Alertas" });
    expect(within(alertas).getByText("Retraso (SPI)")).toHaveAttribute("title", "AL-1");
    expect(within(alertas).queryByText("AL-1")).toBeNull();
    expect(within(alertas).getByText("0,8500 (supuesto declarado)")).toHaveAttribute("title", "0.8500 (SUPUESTO_DECLARADO)");
    expect(screen.getByText("Término por el índice: dia 12 (2026-11-18)")).toBeInTheDocument();
    expect(screen.getByText(/Punto de equilibrio proyectado: no disponible/)).toBeInTheDocument();
    expect(screen.getByText(/V' = V/)).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Plan reproyectado" })).toBeInTheDocument();
  });

  test("sin valuaciones el calculo dice que hacer", async () => {
    calculo = () => json({ ...CALCULO, estado: "sin_valuaciones" });
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valor ganado" }));
    expect(await screen.findByText("Registre la primera valuación para ver el control")).toBeInTheDocument();
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
    await u.type(screen.getByLabelText(/Día hábil objetivo/), "11");
    await u.click(screen.getByRole("button", { name: "Calcular opciones" }));
    expect(await screen.findByRole("table", { name: "Opciones de recuperación" })).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "Horas extra" })).toBeNull(); // no aplica: no se puede elegir
    await u.click(screen.getByRole("radio", { name: "Frentes en paralelo" }));
    await u.type(screen.getByLabelText("Declaro que estas partidas no dependen de las que están en curso (con su fuente)"), "plano 3");
    await u.type(screen.getByLabelText("Fuente de la decisión"), "reunion");
    await u.click(screen.getByRole("button", { name: "Elegir y crear la versión" }));
    expect(await screen.findByText("Versión OB-002 creada con el plan de la opción elegida.")).toBeInTheDocument();
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
    expect(screen.queryByRole("button", { name: "Elegir y crear la versión" })).toBeNull();
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
