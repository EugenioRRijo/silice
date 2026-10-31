import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { ErrorDeApi } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { alertaConTexto } from "../../test/ayudas";
import PaginaControl from "./index";
import { TITULOS_VISIBLES, columnasDe, consultaDeCalculo, descripcionEsVe, errorDeCarga, etiquetaDeCodigo, textoLlano, cuerpoDeOpciones, FILTROS_INICIALES, notaDeOpcion, sinLineasVacias } from "./logica";
import type { Calculo, LineaBase, OpcionDeRecuperacion, Valuaciones } from "./logica";
// VD-1: la respuesta real de POST /v1/control/recuperacion/opciones para OB-S2 (la compara con la API
// `tests/unit/test_api_control.py::test_la_respuesta_de_opciones_del_front_es_la_de_la_api_real`).
import opcionesReales from "./opciones_ob_s2.json";
import { AYUDA_CIFRAS, MENSAJE_CIFRA } from "../../indicadores/cifraEscrita";

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
  descripcion: "versión OB-001, perspectiva costo, vigente desde 02/11/2026",
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
    { Numero: "V-01", Periodo: "02/11/2026 a 06/11/2026", Fecha: "09/11/2026", Inspector: "<b>Ing. Ficticio</b>", Registrada: "09/11/2026 09:00", Estado: "sin hallazgos", Subtotal: "1000.00", IVA: "160.00", "Total con IVA": "1160.00" },
  ],
  impuestos: {
    subtotal: "1000.00",
    iva: "160.00",
    total: "1160.00",
    alicuota: "0.16",
    fuente_alicuota: "Decreto 3.584, G.O. 6.395 Ext., 17-08-2018 (16 %) — a cotejar con la Gaceta vigente",
  },
  perspectiva: "costo",
  aviso: "",
  anulables: [{ id: 7, rotulo: "V-01 (02/11/2026 a 06/11/2026)" }],
  corte_por_defecto: "2026-11-13",
  causas: [{ clave: "compra_tardia", nombre: "Compra tardía" }],
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
  costos_sin_tasa: ["El costo de 10 USD del 01/11/2026 no tiene tasa aplicable."],
  curva: [
    { periodo: "P1", pv: "1000.00", ev: "800.00", ac: "900.00" },
    { periodo: "P2", pv: "2000.00", ev: "1200.00", ac: null },
  ],
  spi_no_aplica: false,
  alertas: [{ Alerta: "AL-1", Severidad: "ERROR", Descripcion: "Retraso", Observado: "0.8000", Umbral: "0.8500 (SUPUESTO_DECLARADO)" }],
  terminos: { indice: "día 12 (18/11/2026)", reproyectado: "día 13 (19/11/2026)", plan_base: "día 10 (13/11/2026)", eac_sistema: "no disponible" },
  motivo_termino: "",
  equilibrio: null,
  estudios: "Sin estudio de reajuste guardado: V' = V. Nunca se proyecta un reajuste.",
  reproyeccion: [{ Partida: "OB-A", Indice: "0.8000", "Fin (dia habil)": "12.50", Nota: "" }],
  plan: { columnas: ["Periodo", "OB-A"], filas: [{ Periodo: "P3", "OB-A": "0.5000" }] },
  decisiones: [],
  versiones_revaloradas: ["OB-R1"],
  atrasos: [],
  precios_convertidos: [],
};

const OPCIONES: OpcionDeRecuperacion[] = [
  { clave: "cuadrillas", titulo: "Cuadrillas adicionales", aplica: true, motivo: "", requisitos: [], requiere_declaracion: false, fila: { Opcion: "Cuadrillas adicionales", Termino: "dia 11", "Retraso (dias)": "1", "Costo directo adicional": "100.00", "Costo indirecto": "0.00", Penalizacion: "0.00", "Punto de equilibrio": "no aplica", Nota: "" } },
  { clave: "frentes", titulo: "Frentes en paralelo", aplica: true, motivo: "", requisitos: ["plano de interferencias"], requiere_declaracion: true, fila: { Opcion: "Frentes en paralelo", Termino: "dia 10", "Retraso (dias)": "0", "Costo directo adicional": "50.00", "Costo indirecto": "0.00", Penalizacion: "0.00", "Punto de equilibrio": "no aplica", Nota: "" } },
  { clave: "horas_extra", titulo: "Horas extra", aplica: false, motivo: "supera el tope legal", requisitos: [], requiere_declaracion: false, fila: { Opcion: "Horas extra", Nota: "supera el tope legal" } },
];

// VD-5: los `title` de una tabla, en orden. El exacto a un toque es para las cifras; un rotulo, un codigo o una fecha
// no llevan `title` (al pasar el raton mostraban el valor interno).
function titulosDe(tabla: HTMLElement): string[] {
  return [...tabla.querySelectorAll("[title]")].map((e) => e.getAttribute("title") ?? "");
}

describe("Control de obra", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let calculo: () => Response;
  let valuaciones: () => Response;
  let lineaBase: () => Response;
  // Tarea 26: «Antes y después» de Recuperación (por omisión, sin línea base que comparar).
  let antesYDespues: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    antesYDespues = () =>
      json({ linea_base: null, version: "OB-001", moneda: "Bs", filas: [], aviso: "Esta obra no tiene línea base." });
    calculo = () => json(CALCULO);
    valuaciones = () => json(VALUACIONES);
    lineaBase = () => json(LINEA_BASE);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = String(entrada);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/control/linea-base") && metodo === "GET") return lineaBase();
      if (url.startsWith("/v1/control/valuaciones") && metodo === "GET") return valuaciones();
      if (url.startsWith("/v1/control/calculo")) return calculo();
      if (url === "/v1/control/valuaciones") return json({ corte: "2026-11-20", hallazgos: 2, errores: 1 });
      if (url === "/v1/control/recuperacion/opciones") return json({ opciones: OPCIONES });
      if (url === "/v1/control/recuperacion/elegir") return json({ version: "OB-002" });
      if (url === "/v1/control/linea-base") return json({ descripcion: "x" });
      if (url.startsWith("/v1/hoja/antes-y-despues")) return antesYDespues();
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

  test("las valuaciones muestran subtotal, IVA y total con IVA en es-VE, con la alícuota y su fuente (Tarea 18)", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    const tabla = await screen.findByRole("table", { name: "Valuaciones registradas" });
    for (const encabezado of ["Subtotal", "IVA", "Total con IVA"]) {
      expect(within(tabla).getByRole("columnheader", { name: encabezado })).toBeInTheDocument();
    }
    expect(within(tabla).getAllByText("1.000,00").length).toBeGreaterThan(0);
    expect(within(tabla).getByText("160,00")).toBeInTheDocument();
    expect(within(tabla).getByText("1.160,00")).toBeInTheDocument();
    const nota = screen.getByText(/IVA al 16 %/);
    expect(nota.textContent).toContain("a cotejar con la Gaceta vigente");
    expect(nota.textContent).toContain("1.160,00");
  });

  test("con la línea base en costo la nota del IVA avisa que no es facturable (T18-3)", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    await screen.findByRole("table", { name: "Valuaciones registradas" });
    expect(screen.getByText(/IVA al 16 %/).textContent).toContain(
      "La línea base está en costo directo: este IVA no es una cifra facturable.",
    );
  });

  test("con la línea base en precio la nota del IVA no lleva ese aviso (T18-3)", async () => {
    valuaciones = () => json({ ...VALUACIONES, perspectiva: "precio" });
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    await screen.findByRole("table", { name: "Valuaciones registradas" });
    expect(screen.getByText(/IVA al 16 %/).textContent).not.toContain("no es una cifra facturable");
  });

  test("la columna Número muestra el número que manda la API con la clave Numero (VB-3)", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    const tabla = await screen.findByRole("table", { name: "Valuaciones registradas" });
    expect(within(tabla).getByText("V-01")).toBeInTheDocument();
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
    expect(await screen.findByText(/perspectiva costo, vigente desde 02\/11\/2026/)).toBeInTheDocument();
    const tabla = screen.getByRole("table", { name: "Parámetros de control" });
    // V-22: la naturaleza y el parametro se leen en español. VD-5: sin el codigo en el title; solo el valor lo lleva
    expect(within(tabla).getAllByText("Supuesto declarado")[0]).toBeInTheDocument();
    expect(within(tabla).getByText("Dato del contrato")).toBeInTheDocument();
    expect(within(tabla).getByText("Umbral de SPI para error")).toBeInTheDocument();
    expect(within(tabla).getByText("SPI por debajo del cual el retraso es ERROR")).toBeInTheDocument();
    expect(titulosDe(tabla)).toEqual(["0.80", "0"]);
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

  test("la pestaña de valuaciones no muestra codigos de la especificacion y lleva sus tildes (VB-5)", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    await screen.findByRole("table", { name: "Valuaciones registradas" });
    const visible = document.body.textContent ?? "";
    expect(visible).not.toMatch(/S\d-R\d+|R13-R14|calculo|linea\b|importacion/);
    expect(screen.getByText(/solo anularla la saca del cálculo\./)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Agregar línea" })).toBeInTheDocument();
  });

  test("el texto del usuario con forma de fecha sale tal cual: solo se formatean las ranuras de fecha (ronda 1)", async () => {
    // La API ya escribe dd/mm/aaaa al armar sus frases (tests/unit/test_api_control.py); el número de la valuación y el
    // código de la versión los escribió el usuario y no se tocan.
    valuaciones = () =>
      json({
        ...VALUACIONES,
        filas: [{ ...VALUACIONES.filas[0], Numero: "2026-11-10" }],
        anulables: [{ id: 7, rotulo: "2026-11-10 (02/11/2026 a 06/11/2026)" }],
      });
    lineaBase = () => json({ ...LINEA_BASE, descripcion: "versión 2026-11-10, perspectiva costo, vigente desde 02/11/2026" });
    const u = montar();
    expect(await screen.findByText("versión 2026-11-10, perspectiva costo, vigente desde 02/11/2026")).toBeInTheDocument();
    await u.click(screen.getByRole("tab", { name: "Valuaciones" }));
    const tabla = await screen.findByRole("table", { name: "Valuaciones registradas" });
    expect(within(tabla).getByText("2026-11-10")).toBeInTheDocument();
    expect(within(tabla).getByText("02/11/2026 a 06/11/2026")).toBeInTheDocument();
    const anular = screen.getByLabelText("Valuación");
    expect(within(anular).getByRole("option", { name: "2026-11-10 (02/11/2026 a 06/11/2026)" })).toHaveValue("7");
  });

  test("el motivo del término cita partidas del usuario y sale tal cual (ronda 1)", async () => {
    calculo = () => json({ ...CALCULO, terminos: { ...CALCULO.terminos!, reproyectado: "no proyectable" }, motivo_termino: "no proyectable: 2026-11-10" });
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Alertas y reproyección" }));
    expect(await screen.findByText("no proyectable: 2026-11-10")).toBeInTheDocument();
  });

  test("el corte que la API manda como fecha ISO se lee en dd/mm/aaaa; las decisiones ya vienen así (VB-19)", async () => {
    calculo = () =>
      json({
        ...CALCULO,
        decisiones: [{ Version: "OB-002", Opcion: "Más cuadrillas", Corte: "13/11/2026", Termino: "27/11/2026", Fuente: "acta 2026-11-10", Responsable: "ana" }],
      });
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valor ganado" }));
    await screen.findByRole("table", { name: "Indicadores de valor ganado" });
    expect(screen.getByText(/^Corte 13\/11\/2026 \(día hábil 10\)/)).toBeInTheDocument();
    expect(screen.getByText(/El costo de 10 USD del 01\/11\/2026/)).toBeInTheDocument();
    await u.click(screen.getByRole("tab", { name: "Recuperación" }));
    const decisiones = await screen.findByRole("table", { name: "Decisiones tomadas" });
    expect(within(decisiones).getByText("13/11/2026")).toBeInTheDocument();
    expect(within(decisiones).getByText("acta 2026-11-10")).toBeInTheDocument();
  });

  test("los feriados se escriben en dd/mm/aaaa y viajan a la API en AAAA-MM-DD (VB-19)", async () => {
    const u = montar();
    await screen.findByText(/perspectiva costo/);
    const feriados = screen.getByLabelText("Feriados (fechas como 25/12/2026, separadas por comas)");
    await u.type(feriados, "25/12/2026, 01/01/2027");
    await u.click(screen.getByRole("button", { name: "Declarar línea base" }));
    await screen.findByText("Línea base declarada.");
    expect(cuerpoDe("/v1/control/linea-base")).toMatchObject({ feriados: "2026-12-25, 2027-01-01" });
  });

  test("un feriado imposible se rechaza antes de enviar, con la fecha que escribió la persona (ronda 1, punto 2)", async () => {
    const u = montar();
    await screen.findByText(/perspectiva costo/);
    await u.type(screen.getByLabelText("Feriados (fechas como 25/12/2026, separadas por comas)"), "31/02/2026");
    await u.click(screen.getByRole("button", { name: "Declarar línea base" }));
    expect((await alertaConTexto()).textContent).toContain(
      "Escriba los feriados como dd/mm/aaaa, separados por comas: «31/02/2026» no es una fecha.",
    );
    expect(cuerpoDe("/v1/control/linea-base")).toBeUndefined();
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
    await u.click(screen.getByRole("button", { name: "Agregar línea" }));
    await u.type(screen.getByLabelText("Fuente (acta, oficio)"), "acta 3");
    await u.click(screen.getByRole("button", { name: "Registrar y controlar" }));
    expect(
      await screen.findByText("Valuación registrada: corte 20/11/2026, 2 hallazgo(s) en la revisión de la valuación (1 con severidad Error)."),
    ).toBeInTheDocument();
    const cuerpo = cuerpoDe("/v1/control/valuaciones");
    expect(cuerpo).toMatchObject({ proyecto: "OB-S2", numero: "V-03", fuente: "acta 3" });
    expect(cuerpo?.lineas).toEqual([{ partida: "OB-A", cantidad: "50", fecha_medicion: "", observacion: "", causa: null }]);
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

  // Tarea D2: con los precios declarados, los que se convirtieron de otra moneda salen con su cuenta, su fecha y su
  // fuente, para quien revise despues (socios y economistas). 31,5 x 36,5 = 1149,75.
  test("valor ganado: los precios convertidos con la tasa del BCV salen con su equivalencia", async () => {
    calculo = () =>
      json({
        ...CALCULO,
        precios_convertidos: [
          {
            descripcion: "Cemento gris",
            unidad: "saco",
            fecha: "2026-10-20",
            fuente: "Estudio de mercado: precio propio",
            equivalencia: {
              precio_original: "31.50",
              moneda_original: "USD",
              tasa: "36.50",
              fecha_tasa: "2026-10-20",
              fuente_tasa: "importacion:3",
              fuente_legible: "BCV, publicación del 20/10/2026",
              convertido: "1149.75",
              moneda: "Bs",
              operacion: "×",
            },
          },
        ],
      });
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valor ganado" }));
    const bloque = (await screen.findByRole("heading", { name: "Precios convertidos con la tasa del BCV" })).closest(
      "section",
    )!;
    expect(within(bloque).getByText("Cemento gris (por saco), desde el 20/10/2026:")).toBeInTheDocument();
    expect(
      within(bloque).getByText("31,50 USD × 36,50 Bs/USD (BCV, publicación del 20/10/2026) = 1.149,75 Bs"),
    ).toBeInTheDocument();
    expect(within(bloque).getByText("Fuente del precio: Estudio de mercado: precio propio.")).toBeInTheDocument();
  });

  test("valor ganado: sin precios convertidos no hay bloque de equivalencias", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valor ganado" }));
    await screen.findByRole("table", { name: "Indicadores de valor ganado" });
    expect(screen.queryByRole("heading", { name: "Precios convertidos con la tasa del BCV" })).toBeNull();
  });

  test("alertas y reproyeccion: terminos, estudios y plan", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Alertas y reproyección" }));
    const alertas = await screen.findByRole("table", { name: "Alertas" });
    expect(within(alertas).getByText("Retraso (SPI)")).toBeInTheDocument();
    expect(within(alertas).queryByText("AL-1")).toBeNull();
    // VD-5: el umbral lleva el exacto de su cifra; la alerta, la descripcion y la naturaleza, ningun title
    expect(alertas.textContent).toContain("0,8500 (supuesto declarado)");
    expect(within(alertas).getByText("0,8500")).toHaveAttribute("title", "0.8500");
    expect(titulosDe(alertas)).toEqual(["0.8000", "0.8500"]);
    expect(screen.getByText("Término por el índice: día 12 (18/11/2026)")).toBeInTheDocument();
    expect(screen.getByText(/Punto de equilibrio proyectado: no disponible/)).toBeInTheDocument();
    expect(screen.getByText(/V' = V/)).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Plan reproyectado" })).toBeInTheDocument();
  });

  test("la severidad de las alertas va con su icono y su nombre, y la descripcion en es-VE (VB-4)", async () => {
    // Las severidades tal como las manda la API (`Severidad.name` del nucleo o «sin evaluar»).
    calculo = () =>
      json({
        ...CALCULO,
        alertas: [
          { Alerta: "AL-1", Severidad: "ADVERTENCIA", Descripcion: "retraso: SPI 0.9780", Observado: "0.9780", Umbral: "0.9500 (SUPUESTO_DECLARADO)" },
          { Alerta: "AL-2", Severidad: "sin evaluar", Descripcion: "CPI no disponible", Observado: "", Umbral: "" },
        ],
      });
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Alertas y reproyección" }));
    const alertas = await screen.findByRole("table", { name: "Alertas" });
    const advertencia = within(alertas).getByText("Advertencia");
    expect(advertencia.closest(".silice-sev")?.querySelector("svg")).not.toBeNull();
    expect(within(alertas).queryByText("ADVERTENCIA")).toBeNull();
    const sinEvaluar = within(alertas).getByText("Sin evaluar");
    expect(sinEvaluar.closest(".silice-sev")?.querySelector("svg")).not.toBeNull();
    expect(within(alertas).getByText("retraso: SPI 0,9780")).toBeInTheDocument();
    expect(within(alertas).queryByText("retraso: SPI 0.9780")).toBeNull();
    // VD-5: la descripcion es texto (su cifra ya se lee entera); el title queda en Observado y en la cifra del umbral
    expect(titulosDe(alertas)).toEqual(["0.9780", "0.9500"]);
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

  test("recuperacion: muestra «Antes y después» de las partidas cambiadas y lo pide para la obra (Tarea 26)", async () => {
    antesYDespues = () =>
      json({
        linea_base: "OB-001",
        version: "OB-002",
        moneda: "Bs",
        aviso: null,
        filas: [
          {
            partida: "OBRA-02",
            descripcion: "Concreto para fundaciones",
            unidad: "m3",
            cantidad: "12",
            costo_antes: { texto: "210.33", exacto: "210.3333333333333333333333333" },
            costo_despues: { texto: "367.75", exacto: "367.75" },
            duracion_antes: "2",
            duracion_despues: "3",
            termino_antes: 58,
            termino_despues: 59,
            equilibrio_antes: null,
            equilibrio_despues: null,
          },
        ],
      });
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Recuperación" }));
    expect(await screen.findByRole("heading", { name: "Antes y después de las partidas cambiadas" })).toBeInTheDocument();
    const tabla = await screen.findByRole("table", { name: "Antes y después de las partidas cambiadas" });
    expect(within(tabla).getByRole("row", { name: /OBRA-02/ })).toHaveTextContent("210,33 Bs pasa a 367,75 Bs");
    const pedidas = fetchFalso.mock.calls.map(([url]) => String(url)).filter((url) => url.startsWith("/v1/hoja/antes-y-despues"));
    expect(pedidas).toContain("/v1/hoja/antes-y-despues?proyecto=OB-S2");
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

  test("la nota de las opciones reales se lee en español: sin códigos, «eficiencia» y cifras en es-VE (VD-1)", async () => {
    const reales = opcionesReales.opciones as OpcionDeRecuperacion[];
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = String(entrada);
      if (url === "/v1/control/recuperacion/opciones") return json(opcionesReales);
      if (url.startsWith("/v1/control/linea-base") && (init?.method ?? "GET") === "GET") return lineaBase();
      if (url.startsWith("/v1/control/calculo")) return calculo();
      return json({ detalle: `ruta inesperada ${url}` }, 500);
    });
    expect(reales).toHaveLength(4);
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Recuperación" }));
    await u.click(await screen.findByRole("button", { name: "Calcular opciones" }));
    const tabla = await screen.findByRole("table", { name: "Opciones de recuperación" });
    // Oráculos escritos a mano: los supuestos de `core/budget/recuperacion.py` con los valores por omisión de
    // `ParametrosControl` (η = 0,80; 3 cuadrillas; 2 h; recargo 0,50; penalización 0).
    const comunes =
      "penalización diaria: 0 (dato del contrato); costo diario de la cuadrilla: composiciones de la línea base " +
      "(supuesto declarado); costo fijo en el tiempo: CF' = CF · D'/D (supuesto declarado)";
    const notas = [
      "eficiencia de la cuadrilla adicional: 0,80 (supuesto declarado); cuadrillas máximas: 3 (supuesto declarado); " + comunes,
      "horas extra por día: 2 (supuesto declarado); eficiencia de la hora extra: 0,80 (supuesto declarado); " +
        "recargo de las horas extra: 0,50 (fuente verificada); FCAS sobre las horas extra: sí (supuesto declarado); " +
        "jornada ordinaria: 8 h (fuente verificada); límites de horas extra: 10 h por semana, 100 h por año " +
        "(fuente verificada); " + comunes,
      "ninguna partida sin empezar con inicio posterior al período siguiente",
      comunes,
    ];
    for (const nota of notas) expect(within(tabla).getByText(nota)).toBeInTheDocument();
    const texto = tabla.textContent ?? "";
    for (const crudo of ["SUPUESTO_DECLARADO", "DATO_DEL_CONTRATO", "FUENTE_VERIFICADA", "eta de", "0.80", "0.50"]) {
      expect(texto).not.toContain(crudo);
    }
  });

  test("quien no puede decidir ve las opciones pero no el boton de elegir", async () => {
    const u = montar("OB-S2", { ...SESION, acciones: ["control_de_obra"] });
    await u.click(await screen.findByRole("tab", { name: "Recuperación" }));
    await u.click(await screen.findByRole("button", { name: "Calcular opciones" }));
    expect(await screen.findByText(/pero no elegir una/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Elegir y crear la versión" })).toBeNull();
  });
});

describe("Control de obra: coma decimal y punto de miles (regla de Eugenio, 2026-10-25)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = String(entrada);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/control/linea-base") && metodo === "GET") return json(LINEA_BASE);
      if (url.startsWith("/v1/control/valuaciones") && metodo === "GET") return json(VALUACIONES);
      if (url.startsWith("/v1/control/calculo")) return json(CALCULO);
      if (url === "/v1/control/valuaciones") return json({ corte: "2026-11-20", hallazgos: 0, errores: 0 });
      if (url === "/v1/control/costos") return json({});
      if (url === "/v1/control/parametros") return json({ cambiados: 1 });
      if (url === "/v1/control/recuperacion/opciones") return json({ opciones: OPCIONES });
      return json({ detalle: `ruta inesperada ${metodo} ${url}` }, 500);
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  function montar() {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: "OB-S2",
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
  const envios = (ruta: string) =>
    fetchFalso.mock.calls.filter(([u, i]) => String(u) === ruta && (i?.method ?? "GET") === "POST");
  const cuerpo = (ruta: string) => JSON.parse(String(envios(ruta).at(-1)?.[1]?.body)) as Record<string, unknown>;

  test("el parametro elegido se edita con coma («0.80» se ve «0,80») y, sin tocarlo, viaja con punto", async () => {
    const u = montar();
    await screen.findByRole("table", { name: "Parámetros de control" });
    await u.selectOptions(screen.getByLabelText("Parámetro a cambiar"), "spi_error");
    const campo = screen.getByLabelText("Nuevo valor de Umbral de SPI para error");
    expect(campo).toHaveValue("0,80");
    expect(screen.getAllByText(AYUDA_CIFRAS).length).toBeGreaterThan(0);
    await u.click(screen.getByRole("button", { name: "Guardar parámetros" }));
    await screen.findByText("1 parámetro(s) cambiado(s).");
    expect(cuerpo("/v1/control/parametros").parametros).toEqual([{ parametro: "spi_error", valor: "0.80" }]);
  });

  test("un parametro escrito con punto decimal se rechaza junto al campo y no se envia", async () => {
    const u = montar();
    await screen.findByRole("table", { name: "Parámetros de control" });
    await u.selectOptions(screen.getByLabelText("Parámetro a cambiar"), "spi_error");
    const campo = screen.getByLabelText("Nuevo valor de Umbral de SPI para error");
    await u.clear(campo);
    await u.type(campo, "0.85");
    await u.click(screen.getByRole("button", { name: "Guardar parámetros" }));
    expect(await screen.findByText(MENSAJE_CIFRA)).toBeInTheDocument();
    expect(envios("/v1/control/parametros")).toHaveLength(0);
    await u.clear(campo);
    await u.type(campo, "0,85");
    await u.click(screen.getByRole("button", { name: "Guardar parámetros" }));
    await screen.findByText("1 parámetro(s) cambiado(s).");
    expect(cuerpo("/v1/control/parametros").parametros).toEqual([{ parametro: "spi_error", valor: "0.85" }]);
  });

  test("la cantidad de una valuacion se escribe con coma y punto de miles; con punto decimal no se envia", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    await screen.findByRole("table", { name: "Valuaciones registradas" });
    await u.type(screen.getByLabelText("Partida 1"), "OB-A");
    await u.type(screen.getByLabelText("Cantidad 1"), "2.5");
    await u.click(screen.getByRole("button", { name: "Registrar y controlar" }));
    expect(await screen.findByText(MENSAJE_CIFRA)).toBeInTheDocument();
    expect(envios("/v1/control/valuaciones")).toHaveLength(0);
    await u.clear(screen.getByLabelText("Cantidad 1"));
    await u.type(screen.getByLabelText("Cantidad 1"), "1.234,5");
    await u.click(screen.getByRole("button", { name: "Registrar y controlar" }));
    await screen.findByText(/Valuación registrada/);
    expect(cuerpo("/v1/control/valuaciones").lineas).toEqual([
      { partida: "OB-A", cantidad: "1234.5", fecha_medicion: "", observacion: "", causa: null },
    ]);
  });

  test("el monto de un costo «1.000» es mil, no uno", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    await screen.findByRole("table", { name: "Valuaciones registradas" });
    await u.type(screen.getByLabelText("Monto"), "1.000");
    await u.click(screen.getByRole("button", { name: "Anotar costo" }));
    await screen.findByText(/Costo anotado/);
    expect(cuerpo("/v1/control/costos")).toMatchObject({ monto: "1000" });
  });

  test("el monto de un costo con punto decimal se rechaza y no se envia", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    await screen.findByRole("table", { name: "Valuaciones registradas" });
    await u.type(screen.getByLabelText("Monto"), "12.50");
    await u.click(screen.getByRole("button", { name: "Anotar costo" }));
    expect(await screen.findByText(MENSAJE_CIFRA)).toBeInTheDocument();
    expect(envios("/v1/control/costos")).toHaveLength(0);
  });

  test("las horas extra previas viajan con punto; escritas con punto decimal no se calculan", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Recuperación" }));
    const horas = await screen.findByLabelText("Horas extra que el obrero ya acumula en el año");
    await u.clear(horas);
    await u.type(horas, "2.5");
    await u.click(screen.getByRole("button", { name: "Calcular opciones" }));
    expect(await screen.findByText(MENSAJE_CIFRA)).toBeInTheDocument();
    expect(envios("/v1/control/recuperacion/opciones")).toHaveLength(0);
    await u.clear(horas);
    await u.type(horas, "1.002,5");
    await u.click(screen.getByRole("button", { name: "Calcular opciones" }));
    await screen.findByRole("table", { name: "Opciones de recuperación" });
    expect(cuerpo("/v1/control/recuperacion/opciones")).toMatchObject({ horas_previas: "1002.5" });
  });

  test("Km y R de la escalatoria se escriben con coma; con punto decimal no se calcula", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valor ganado" }));
    await screen.findByRole("table", { name: "Indicadores de valor ganado" });
    await u.selectOptions(screen.getByLabelText("Precios del corte"), "escalatoria");
    await u.type(screen.getByLabelText("Km declarado"), "1.05");
    await u.click(screen.getByRole("button", { name: "Calcular al corte" }));
    expect(await screen.findByText(MENSAJE_CIFRA)).toBeInTheDocument();
    expect(fetchFalso.mock.calls.some(([url]) => String(url).includes("metodo=escalatoria"))).toBe(false);
    await u.clear(screen.getByLabelText("Km declarado"));
    await u.type(screen.getByLabelText("Km declarado"), "1,05");
    await u.clear(screen.getByLabelText("R declarado"));
    await u.type(screen.getByLabelText("R declarado"), "0,15");
    await u.click(screen.getByRole("button", { name: "Calcular al corte" }));
    await waitFor(() =>
      expect(fetchFalso.mock.calls.some(([url]) => String(url).includes("km=1.05&r=0.15"))).toBe(true),
    );
  });
});

describe("logica del control", () => {
  test("la consulta del calculo solo lleva lo elegido", () => {
    expect(consultaDeCalculo("OB S2", FILTROS_INICIALES)).toBe("/v1/control/calculo?proyecto=OB+S2");
    // Km y R se escriben con coma (regla de Eugenio, 2026-10-25) y viajan con punto.
    const con = consultaDeCalculo("P", { corte: " 2026-11-06 ", precios: { metodo: "escalatoria", version: "x", km: "1,1", r: "0", fuente: "f" } });
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

  test("descripcionEsVe pone en es-VE solo las cifras de las frases fijas de las alertas (VB-4)", () => {
    expect(descripcionEsVe("retraso: SPI 0.9780")).toBe("retraso: SPI 0,9780");
    expect(descripcionEsVe("sobrecosto: CPI 0.8125")).toBe("sobrecosto: CPI 0,8125");
    expect(
      descripcionEsVe(
        "evaluar el reajuste (S1; LCP art. 133, a cotejar): el precio del corte desvía -1250.50 sobre un valor ganado de 4266.67",
      ),
    ).toBe("evaluar el reajuste (S1; LCP art. 133, a cotejar): el precio del corte desvía -1.250,50 sobre un valor ganado de 4.266,67");
    expect(
      descripcionEsVe("el punto de equilibrio proyectado sube más de 5.0 puntos porcentuales sobre el de la línea base"),
    ).toBe("el punto de equilibrio proyectado sube más de 5,0 puntos porcentuales sobre el de la línea base");
    // el codigo de una partida lo escribe el usuario: no se toca aunque parezca una cifra
    const detenida = "la partida 1.01 tiene trabajo planificado y ningún avance (detenida)";
    expect(descripcionEsVe(detenida)).toBe(detenida);
    expect(descripcionEsVe("CPI no disponible")).toBe("CPI no disponible");
  });

  test("descripcionEsVe devuelve intacto un texto hostil de 100 000 caracteres en menos de un segundo (ronda 1, punto 5)", () => {
    const hostiles = [
      "x" + ": el precio del corte desvía 1 sobre un valor ganado de ".repeat(1_800) + "z",
      "el punto de equilibrio proyectado sube más de " + "1".repeat(100_000) + "x",
      ": el precio del corte desvía ".repeat(3_500),
      // la frase calza y la cifra es enorme: el separador de miles de formatoEsVe es cuadratico en su largo
      "retraso: SPI " + "1".repeat(100_000),
      "evaluar el reajuste: el precio del corte desvía " + "9".repeat(50_000) + " sobre un valor ganado de " + "9".repeat(50_000),
    ];
    for (const texto of hostiles) {
      const inicio = performance.now();
      expect(descripcionEsVe(texto)).toBe(texto);
      const ms = performance.now() - inicio;
      console.log(`descripcionEsVe ${texto.length} car.: ${ms.toFixed(1)} ms`);
      expect(ms).toBeLessThan(1_000);
    }
    // por debajo del tope sigue formateando
    expect(descripcionEsVe("retraso: SPI 0.9780")).toBe("retraso: SPI 0,9780");
  }, 120_000);

  test("notaDeOpcion presenta cada ranura por separado y deja intacto lo que escribió el usuario (VD-1)", () => {
    const base = opcionesReales.opciones[0] as OpcionDeRecuperacion;
    const con = (supuestos: { nombre: string; valor: string; naturaleza: string }[]): OpcionDeRecuperacion => ({
      ...base,
      supuestos,
    });
    // la independencia lista códigos de partida del usuario: ni sus códigos ni sus cifras cambian
    const independencia = "dia, SUPUESTO_DECLARADO, 1.50, eta de cuadrillas";
    expect(
      notaDeOpcion(con([{ nombre: "independencia de las partidas", valor: independencia, naturaleza: "SUPUESTO_DECLARADO" }])),
    ).toBe(`independencia de las partidas: ${independencia} (supuesto declarado)`);
    // la cifra se pone en es-VE solo en los supuestos numéricos del núcleo, y solo si toda la ranura es una cifra
    expect(notaDeOpcion(con([{ nombre: "penalización diaria", valor: "1500.25", naturaleza: "DATO_DEL_CONTRATO" }]))).toBe(
      "penalización diaria: 1.500,25 (dato del contrato)",
    );
    expect(notaDeOpcion(con([{ nombre: "recargo", valor: "0.50 por hora", naturaleza: "FUENTE_VERIFICADA" }]))).toBe(
      "recargo de las horas extra: 0.50 por hora (fuente verificada)",
    );
    expect(notaDeOpcion(con([{ nombre: "otro supuesto", valor: "0.80", naturaleza: "NATURALEZA_NUEVA" }]))).toBe(
      "otro supuesto: 0.80 (NATURALEZA_NUEVA)",
    );
    // la que no aplica (o una API sin ranuras) muestra su nota tal cual
    const sinAplicar = opcionesReales.opciones[2] as OpcionDeRecuperacion;
    expect(notaDeOpcion(sinAplicar)).toBe(sinAplicar.fila.Nota);
    expect(notaDeOpcion({ ...base, supuestos: undefined })).toBe(base.fila.Nota);
  });

  test("notaDeOpcion con ranuras hostiles de 100 000 caracteres responde en menos de un segundo (VD-1)", () => {
    const base = opcionesReales.opciones[0] as OpcionDeRecuperacion;
    const hostiles = [
      { nombre: "penalización diaria", valor: "9".repeat(100_000), naturaleza: "DATO_DEL_CONTRATO" },
      { nombre: "independencia de las partidas", valor: "SUPUESTO_DECLARADO; ".repeat(5_000), naturaleza: "SUPUESTO_DECLARADO" },
      { nombre: "eta de cuadrillas".repeat(6_000), valor: "0.80", naturaleza: "SUPUESTO_DECLARADO" },
      { nombre: "recargo", valor: "1." + "0".repeat(100_000) + "x", naturaleza: "F".repeat(100_000) },
    ];
    for (const s of hostiles) {
      const inicio = performance.now();
      const nota = notaDeOpcion({ ...base, supuestos: [s] });
      const ms = performance.now() - inicio;
      console.log(`notaDeOpcion ${s.nombre.length + s.valor.length + s.naturaleza.length} car.: ${ms.toFixed(1)} ms`);
      expect(ms).toBeLessThan(1_000);
      // una ranura fuera de tope sale tal cual
      expect(nota).toContain(s.valor);
    }
  }, 120_000);

  test("las lineas sin partida ni cantidad no se mandan", () => {
    const vacia = { partida: "", cantidad: "", fecha_medicion: "2026-11-01", observacion: "" };
    const llena = { partida: "A", cantidad: "", fecha_medicion: "", observacion: "" };
    expect(sinLineasVacias([vacia, llena])).toEqual([llena]);
  });
});

function cuerpoDe_(proyecto: string) {
  return cuerpoDeOpciones(proyecto, FILTROS_INICIALES, "11", "2");
}
