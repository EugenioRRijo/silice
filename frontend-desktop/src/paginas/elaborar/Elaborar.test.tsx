import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { alertaConTexto } from "../../test/ayudas";
import PaginaElaborar from "./index";
import { hoy } from "./logica";
import type { CalculoRespuesta, ItemComputo, PartidaCatalogo, RendimientoPorDeclarar } from "./tipos";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja"],
  modo_entrega: false,
};

const PARTIDAS: PartidaCatalogo[] = [
  { codigo: "FIC-C1", descripcion: "Concreto ficticio", unidad: "m3", dominio: "civil" },
  { codigo: "FIC-C2", descripcion: "Encofrado ficticio", unidad: "m2", dominio: "civil" },
  { codigo: "FIC-C3", descripcion: "Excavacion ficticia", unidad: "m3", dominio: "civil" },
  { codigo: "FIC-C4", descripcion: "Tuberia ficticia", unidad: "m", dominio: "civil" },
];

const item = (origen: string, codigo: string, cantidad = "12.5000"): ItemComputo => ({
  codigo_partida: codigo,
  descripcion: `Descripcion ${origen}`,
  unidad: "m3",
  cantidad,
  origen_id: origen,
  origen_tipo: "tabla",
  dominio: "telecom",
  regla: null,
  parametros: {},
  especificaciones: {},
});

const ITEMS: ItemComputo[] = [item("fila-1", "FIC-T1"), item("fila-2", "FIC-T2", "3.0000")];

const INFORME_VACIO = {
  codigo_presupuesto: "P-001",
  cumple: true,
  veredicto: "CUMPLE",
  total_hallazgos: 0,
  por_severidad: [],
  reglas_evaluadas: [{ regla: "R1", nombre: "Regla uno", hallazgos: 0 }],
  hallazgos: [],
  sin_hallazgos: "Se verifico y no hubo hallazgos.",
};

const PLAN = [
  { periodo: "1", codigo_partida: "FIC-T1", fraccion: "1" },
  { periodo: "2", codigo_partida: "FIC-T2", fraccion: "1" },
];

function calculo(extra: Partial<CalculoRespuesta> = {}): CalculoRespuesta {
  return {
    codigo: "P-001",
    fecha: "2026-10-18",
    moneda: "USD",
    total: "1234.50",
    partidas: [
      {
        codigo_partida: "FIC-T1",
        descripcion: "Descripcion fila-1",
        unidad: "m3",
        cantidad: "12.50",
        precio_unitario: "80.00",
        total: "1000.00",
      },
    ],
    por_severidad: [],
    informe: INFORME_VACIO,
    pendientes: [],
    plan_por_defecto: PLAN,
    ...extra,
  };
}

const CON_HALLAZGOS = calculo({
  por_severidad: [
    { severidad: "ERROR", total: 2 },
    { severidad: "ADVERTENCIA", total: 1 },
  ],
  informe: {
    ...INFORME_VACIO,
    cumple: false,
    veredicto: "NO CUMPLE",
    total_hallazgos: 3,
    sin_hallazgos: null,
    hallazgos: [
      {
        numero: 1,
        regla: "R1",
        severidad: "ERROR",
        partida: "FIC-T1",
        descripcion: "Hallazgo ficticio uno",
        impacto: "10.00",
        observado: "5.00",
        esperado: "4.00",
        origen: ["fila-1"],
      },
    ],
  },
});

const CON_PENDIENTE = calculo({
  pendientes: [
    {
      codigo_partida: "FIC-X",
      descripcion: "Zanja inexistente",
      unidad: "m",
      cantidad: "7.0000",
      origen_id: "fila-9",
      propuestas: [
        { codigo: "FIC-Z1", descripcion: "Zanja tipo uno", puntaje: 0.9137 },
        { codigo: "FIC-Z2", descripcion: "Zanja tipo dos", puntaje: 0.5 },
      ],
      falla: null,
    },
    {
      codigo_partida: "FIC-Y",
      descripcion: "Muro raro",
      unidad: "m2",
      cantidad: "2.0000",
      origen_id: "fila-10",
      propuestas: [],
      falla: "El modelo de similitud no esta disponible.",
    },
  ],
});

const RENDIMIENTO: RendimientoPorDeclarar = {
  codigo_partida: "FIC-T1",
  propuesta: {
    rendimiento: { valor: "8.5", tipo: "estimado", fecha: "2026-01-02", condiciones: "", referencia_ejecucion: null },
    dispersion: { observaciones: 3, medidos: 1, estimados: 2, media: "8.40", minimo: "7.00", maximo: "9.50" },
  },
};
const RENDIMIENTO_SIN_PROPUESTA: RendimientoPorDeclarar = { codigo_partida: "FIC-T2", propuesta: null };

type Manejador = (init: RequestInit | undefined) => Response | Promise<Response>;

describe("Elaborar un presupuesto", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let rutas: Record<string, Manejador>;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fijarCsrf("tok");
    fetchFalso.mockReset();
    rutas = {
      "GET /partidas?dominio=civil": () => json(PARTIDAS),
      "POST /v1/computos/telecom": () => json(ITEMS),
      "POST /v1/computos/civil": () => json(ITEMS),
      "POST /presupuestos/calcular": () => json(calculo()),
    };
    fetchFalso.mockImplementation(async (ruta, init) => {
      const clave = `${init?.method ?? "GET"} ${String(ruta)}`;
      const manejador = rutas[clave];
      if (!manejador) throw new Error(`Ruta sin doble: ${clave}`);
      return manejador(init);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  function montar(alExpirar = vi.fn()) {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: null,
      caso: { nombre: "clinica", ruta_relativa: "data/clinica.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    render(
      <ContextoAplicacion.Provider value={valor}>
        <PaginaElaborar />
      </ContextoAplicacion.Provider>,
    );
    return { alExpirar, usuario: userEvent.setup({ applyAccept: false }) };
  }

  const llamadas = (clave: string) =>
    fetchFalso.mock.calls.filter(([r, i]) => `${i?.method ?? "GET"} ${String(r)}` === clave);
  const cuerpoJson = (clave: string, n = 0) => JSON.parse(String(llamadas(clave)[n][1]?.body)) as Record<string, unknown>;
  const campoArchivo = () => document.querySelector('input[type="file"]') as HTMLInputElement;

  async function irATelecom(usuario: ReturnType<typeof userEvent.setup>) {
    await usuario.selectOptions(screen.getByLabelText("Dominio"), "telecom");
  }

  async function extraerTelecom(usuario: ReturnType<typeof userEvent.setup>) {
    await irATelecom(usuario);
    await usuario.upload(campoArchivo(), new File(["a,b"], "muestra.csv"));
    await usuario.click(screen.getByRole("button", { name: "Extraer cómputo" }));
    await screen.findByText("Cómputo extraído");
  }

  async function elaborar(usuario: ReturnType<typeof userEvent.setup>) {
    await usuario.click(screen.getByRole("button", { name: "Elaborar presupuesto" }));
    await screen.findByText("Presupuesto elaborado");
  }

  test("al abrir muestra la ayuda y los parametros por defecto, con Extraer deshabilitado", async () => {
    montar();
    expect(screen.getByRole("heading", { name: "Elaborar un presupuesto" })).toBeInTheDocument();
    expect(screen.getByText(/carga su archivo de muestra \(data\/samples\/<dominio>\/\)/)).toBeInTheDocument();
    expect(screen.getByLabelText("Código del presupuesto")).toHaveValue("P-001");
    expect(screen.getByLabelText("Moneda")).toHaveValue("USD");
    expect(screen.getByLabelText("Fecha")).toHaveValue(hoy());
    const dominios = within(screen.getByLabelText("Dominio")).getAllByRole("option").map((o) => o.textContent);
    expect(dominios).toEqual(["civil", "telecom", "industrial", "sistemas"]);
    expect(screen.getByRole("button", { name: "Extraer cómputo" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Elaborar presupuesto" })).toBeNull();
    await screen.findByLabelText("Concreto");
  });

  test("civil sin partidas civiles avisa y no deja extraer aunque haya archivo", async () => {
    rutas["GET /partidas?dominio=civil"] = () => json([]);
    const { usuario } = montar();
    expect(await screen.findByText(/El catalogo no tiene partidas del dominio civil todavia/)).toBeInTheDocument();
    await usuario.upload(campoArchivo(), new File(["a"], "muestra.csv"));
    expect(screen.getByRole("button", { name: "Extraer cómputo" })).toBeDisabled();
    expect(screen.queryByLabelText("Concreto")).toBeNull();
  });

  test("si el catalogo no se puede leer muestra el error y el aviso", async () => {
    rutas["GET /partidas?dominio=civil"] = () => json({ detalle: "La base no responde." }, 500);
    montar();
    expect(await alertaConTexto()).toHaveTextContent("La base no responde.");
    expect(screen.getByText(/El catalogo no tiene partidas del dominio civil todavia/)).toBeInTheDocument();
  });

  test("civil con partidas: elige los codigos y manda el mapeo junto al CSV", async () => {
    const { usuario } = montar();
    await screen.findByLabelText("Concreto");
    await usuario.selectOptions(screen.getByLabelText("Encofrado"), "FIC-C2");
    await usuario.selectOptions(screen.getByLabelText("Excavación"), "FIC-C3");
    await usuario.selectOptions(screen.getByLabelText("Tubería"), "FIC-C4");
    expect(screen.queryByLabelText("Relleno")).toBeNull();
    await usuario.upload(campoArchivo(), new File(["a,b"], "muestra.csv"));
    await usuario.click(screen.getByRole("button", { name: "Extraer cómputo" }));
    await screen.findByText("Cómputo extraído");
    const [, init] = llamadas("POST /v1/computos/civil")[0];
    const datos = init?.body as FormData;
    expect((datos.get("archivo") as File).name).toBe("muestra.csv");
    expect(JSON.parse(String(datos.get("codigos")))).toEqual({
      concreto: "FIC-C1",
      encofrado: "FIC-C2",
      excavacion: "FIC-C3",
      tuberia: "FIC-C4",
    });
    expect(new Headers(init?.headers).get("X-Silice-CSRF")).toBe("tok");
  });

  test("la casilla de relleno agrega el selector y la clave relleno", async () => {
    const { usuario } = montar();
    await screen.findByLabelText("Concreto");
    await usuario.click(screen.getByLabelText("Incluir relleno (balance R5)"));
    await usuario.selectOptions(screen.getByLabelText("Relleno"), "FIC-C2");
    await usuario.upload(campoArchivo(), new File(["a"], "muestra.csv"));
    await usuario.click(screen.getByRole("button", { name: "Extraer cómputo" }));
    await screen.findByText("Cómputo extraído");
    const datos = llamadas("POST /v1/computos/civil")[0][1]?.body as FormData;
    expect(JSON.parse(String(datos.get("codigos"))).relleno).toBe("FIC-C2");
  });

  test("otro dominio extrae sin codigos y muestra la tabla del computo", async () => {
    const { usuario } = montar();
    await extraerTelecom(usuario);
    const datos = llamadas("POST /v1/computos/telecom")[0][1]?.body as FormData;
    expect(datos.has("codigos")).toBe(false);
    expect(llamadas("GET /partidas?dominio=civil")).toHaveLength(1);
    const tabla = screen.getByRole("table", { name: "Cómputo extraído" });
    for (const titulo of ["codigo_partida", "descripcion", "unidad", "cantidad", "origen_id", "origen_tipo", "regla"]) {
      expect(within(tabla).getByText(titulo)).toBeInTheDocument();
    }
    expect(within(tabla).getByText("12.5000")).toBeInTheDocument();
    expect(within(tabla).getByText("Descripcion fila-2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Elaborar presupuesto" })).toBeEnabled();
  });

  test("un error al extraer se muestra con su detalle y borra el computo", async () => {
    const { usuario } = montar();
    await extraerTelecom(usuario);
    rutas["POST /v1/computos/telecom"] = () => json({ detail: "Falta la columna cantidad." }, 400);
    await usuario.click(screen.getByRole("button", { name: "Extraer cómputo" }));
    expect(await alertaConTexto()).toHaveTextContent("Falta la columna cantidad.");
    expect(screen.queryByText("Cómputo extraído")).toBeNull();
    expect(screen.queryByRole("button", { name: "Elaborar presupuesto" })).toBeNull();
  });

  test("elabora sin plan, muestra total, severidades, tabla e informe y sigue en la misma pagina", async () => {
    rutas["POST /presupuestos/calcular"] = () => json(CON_HALLAZGOS);
    const { usuario } = montar();
    await extraerTelecom(usuario);
    await usuario.clear(screen.getByLabelText("Código del presupuesto"));
    await usuario.type(screen.getByLabelText("Código del presupuesto"), "P-007");
    await elaborar(usuario);
    expect(cuerpoJson("POST /presupuestos/calcular")).toEqual({
      codigo: "P-007",
      fecha: hoy(),
      moneda: "USD",
      items: ITEMS,
    });
    expect(screen.getByText("Total del presupuesto")).toBeInTheDocument();
    expect(screen.getByText("1234.50 USD")).toBeInTheDocument();
    const metricas = screen.getByRole("group", { name: "Métricas del presupuesto" });
    expect(within(metricas).getByText("ERROR")).toBeInTheDocument();
    expect(within(metricas).getByText("2")).toBeInTheDocument();
    expect(within(metricas).getByText("ADVERTENCIA")).toBeInTheDocument();
    expect(within(metricas).getByText("1")).toBeInTheDocument();
    expect(screen.queryByText(/Sin hallazgos: la auditoria/)).toBeNull();
    const tabla = screen.getByRole("table", { name: "Partidas del presupuesto" });
    expect(within(tabla).getByText("precio_unitario")).toBeInTheDocument();
    expect(within(tabla).getByText("1000.00")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Informe de auditoria" })).toBeInTheDocument();
    expect(screen.getByText("Hallazgo ficticio uno")).toBeInTheDocument();
  });

  test("durante la elaboracion el boton dice Elaborando...", async () => {
    let terminar: (r: Response) => void = () => {};
    const { usuario } = montar();
    await extraerTelecom(usuario);
    rutas["POST /presupuestos/calcular"] = () => new Promise<Response>((r) => (terminar = r));
    await usuario.click(screen.getByRole("button", { name: "Elaborar presupuesto" }));
    expect(await screen.findByRole("button", { name: "Elaborando..." })).toBeDisabled();
    terminar(json(calculo()));
    await screen.findByText("Presupuesto elaborado");
    expect(screen.getByRole("button", { name: "Elaborar presupuesto" })).toBeEnabled();
  });

  test("sin hallazgos muestra el exito", async () => {
    const { usuario } = montar();
    await extraerTelecom(usuario);
    await elaborar(usuario);
    expect(screen.getByText("Sin hallazgos: la auditoria no encontro ninguna inconsistencia.")).toBeInTheDocument();
  });

  test("un error al elaborar sin plan se muestra y borra el resultado anterior", async () => {
    const { usuario } = montar();
    await extraerTelecom(usuario);
    await elaborar(usuario);
    rutas["POST /presupuestos/calcular"] = () => json({ detalle: "No hay lista de precios vigente." }, 409);
    await usuario.click(screen.getByRole("button", { name: "Elaborar presupuesto" }));
    expect(await alertaConTexto()).toHaveTextContent("No hay lista de precios vigente.");
    expect(screen.queryByText("Presupuesto elaborado")).toBeNull();
    expect(screen.queryByText("Rendimientos por declarar")).toBeNull();
  });

  test("Exportar a Excel pide el libro con el mismo cuerpo", async () => {
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: vi.fn(() => "blob:x"), revokeObjectURL: vi.fn() }));
    rutas["POST /presupuestos/calcular/excel"] = () =>
      new Response(new Blob(["xlsx"]), { status: 200, headers: { "Content-Disposition": 'attachment; filename="P-001.xlsx"' } });
    const { usuario } = montar();
    await extraerTelecom(usuario);
    await elaborar(usuario);
    await usuario.click(screen.getByRole("button", { name: "Exportar a Excel" }));
    await waitFor(() => expect(llamadas("POST /presupuestos/calcular/excel")).toHaveLength(1));
    expect(cuerpoJson("POST /presupuestos/calcular/excel")).toEqual(cuerpoJson("POST /presupuestos/calcular"));
  });

  test("lista los pendientes con falla y propuestas, y aceptar una vuelve a elaborar con el codigo cambiado", async () => {
    rutas["POST /v1/computos/telecom"] = () => json([item("fila-1", "FIC-T1"), item("fila-9", "FIC-X", "7.0000")]);
    rutas["POST /presupuestos/calcular"] = () => json(CON_PENDIENTE);
    const { usuario } = montar();
    await extraerTelecom(usuario);
    await elaborar(usuario);
    expect(screen.getByText(/Estos items del computo no tienen partida en el catalogo/)).toBeInTheDocument();
    expect(screen.getByText("fila-9 · FIC-X · Zanja inexistente")).toBeInTheDocument();
    expect(screen.getByText("fila-10 · FIC-Y · Muro raro")).toBeInTheDocument();
    expect(screen.getByText("El modelo de similitud no esta disponible.")).toBeInTheDocument();
    expect(screen.getByText("FIC-Z1 · Zanja tipo uno (0.91)")).toBeInTheDocument();
    expect(screen.getByText("FIC-Z2 · Zanja tipo dos (0.50)")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Aplicar y volver a elaborar" })).toHaveLength(1);

    rutas["POST /presupuestos/calcular"] = () => json(calculo());
    await usuario.selectOptions(screen.getByLabelText("Propuesta para fila-9"), "FIC-Z2");
    await usuario.click(screen.getByRole("button", { name: "Aplicar y volver a elaborar" }));
    await waitFor(() => expect(llamadas("POST /presupuestos/calcular")).toHaveLength(2));
    const items = cuerpoJson("POST /presupuestos/calcular", 1).items as ItemComputo[];
    expect(items.map((i) => i.codigo_partida)).toEqual(["FIC-T1", "FIC-Z2"]);
    await waitFor(() => expect(screen.queryByText("Pendientes")).toBeNull());
  });

  test("aceptar una propuesta con el computo ya cambiado es un error y no calcula", async () => {
    rutas["POST /presupuestos/calcular"] = () => json(CON_PENDIENTE);
    const { usuario } = montar();
    await extraerTelecom(usuario);
    await elaborar(usuario);
    rutas["POST /v1/computos/telecom"] = () => json({ detail: "Archivo roto." }, 400);
    await usuario.click(screen.getByRole("button", { name: "Extraer cómputo" }));
    await alertaConTexto();
    await usuario.click(screen.getByRole("button", { name: "Aplicar y volver a elaborar" }));
    const mensajes = await screen.findAllByText(/El computo cambio despues de esta elaboracion/);
    expect(mensajes.length).toBeGreaterThan(0);
    expect(llamadas("POST /presupuestos/calcular")).toHaveLength(1);
  });

  test("precarga el plan de trabajo con plan_por_defecto", async () => {
    const { usuario } = montar();
    await extraerTelecom(usuario);
    await elaborar(usuario);
    expect(screen.getByRole("heading", { name: "Plan de trabajo" })).toBeInTheDocument();
    expect(screen.getByText(/Distribuya las partidas en periodos/)).toBeInTheDocument();
    expect(screen.getByLabelText("Periodo, fila 1")).toHaveValue("1");
    expect(screen.getByLabelText("Codigo de partida, fila 2")).toHaveValue("FIC-T2");
    expect(screen.getByLabelText("Fraccion, fila 2")).toHaveValue("1");
    expect(screen.queryByText(/el plan editado antes se descarto/)).toBeNull();
  });

  test("aplicar el plan manda las filas editadas en plan y recalcula", async () => {
    const { usuario } = montar();
    await extraerTelecom(usuario);
    await elaborar(usuario);
    const fraccion = screen.getByLabelText("Fraccion, fila 1");
    await usuario.clear(fraccion);
    await usuario.type(fraccion, "0.5");
    await usuario.click(screen.getByRole("button", { name: "Añadir fila" }));
    await usuario.type(screen.getByLabelText("Periodo, fila 3"), "3");
    await usuario.type(screen.getByLabelText("Codigo de partida, fila 3"), "FIC-T1");
    await usuario.type(screen.getByLabelText("Fraccion, fila 3"), "0.5");
    await usuario.click(screen.getByRole("button", { name: "Aplicar plan y volver a elaborar" }));
    await waitFor(() => expect(llamadas("POST /presupuestos/calcular")).toHaveLength(2));
    expect(cuerpoJson("POST /presupuestos/calcular", 1).plan).toEqual([
      { periodo: "1", codigo_partida: "FIC-T1", fraccion: "0.5" },
      { periodo: "2", codigo_partida: "FIC-T2", fraccion: "1" },
      { periodo: "3", codigo_partida: "FIC-T1", fraccion: "0.5" },
    ]);
  });

  test("se puede quitar una fila del plan", async () => {
    const { usuario } = montar();
    await extraerTelecom(usuario);
    await elaborar(usuario);
    await usuario.click(screen.getByRole("button", { name: "Quitar fila 1" }));
    expect(screen.queryByLabelText("Periodo, fila 2")).toBeNull();
    expect(screen.getByLabelText("Codigo de partida, fila 1")).toHaveValue("FIC-T2");
  });

  test("un plan invalido muestra su detalle y deja a la vista el presupuesto anterior", async () => {
    const { usuario } = montar();
    await extraerTelecom(usuario);
    await elaborar(usuario);
    rutas["POST /presupuestos/calcular"] = () => json({ detalle: "Las fracciones de FIC-T1 no suman 1." }, 422);
    await usuario.click(screen.getByRole("button", { name: "Aplicar plan y volver a elaborar" }));
    expect(await alertaConTexto()).toHaveTextContent("Las fracciones de FIC-T1 no suman 1.");
    expect(screen.getByText("Presupuesto elaborado")).toBeInTheDocument();
    expect(screen.getByText("1234.50 USD")).toBeInTheDocument();
    expect(screen.getByLabelText("Periodo, fila 1")).toBeInTheDocument();
  });

  test("avisa si elaborar sin plan descarta una tabla editada, y no si nadie la toco", async () => {
    const { usuario } = montar();
    await extraerTelecom(usuario);
    await elaborar(usuario);
    await usuario.click(screen.getByRole("button", { name: "Elaborar presupuesto" }));
    await waitFor(() => expect(llamadas("POST /presupuestos/calcular")).toHaveLength(2));
    expect(screen.queryByText(/el plan editado antes se descarto/)).toBeNull();

    const fraccion = screen.getByLabelText("Fraccion, fila 1");
    await usuario.clear(fraccion);
    await usuario.type(fraccion, "0.25");
    await usuario.click(screen.getByRole("button", { name: "Elaborar presupuesto" }));
    expect(await screen.findByText(/el plan de trabajo volvio a una partida por dia/)).toBeInTheDocument();
    expect(screen.getByLabelText("Fraccion, fila 1")).toHaveValue("1");
  });

  test("el aviso no se arrastra: si el plan se aplica con exito desaparece", async () => {
    const { usuario } = montar();
    await extraerTelecom(usuario);
    await elaborar(usuario);
    await usuario.type(screen.getByLabelText("Fraccion, fila 1"), "0");
    await usuario.click(screen.getByRole("button", { name: "Elaborar presupuesto" }));
    await screen.findByText(/el plan de trabajo volvio a una partida por dia/);
    await usuario.click(screen.getByRole("button", { name: "Aplicar plan y volver a elaborar" }));
    await waitFor(() => expect(screen.queryByText(/el plan de trabajo volvio a una partida por dia/)).toBeNull());
  });

  test("aplicar el plan sin items guardados pide extraer de nuevo", async () => {
    const { usuario } = montar();
    await extraerTelecom(usuario);
    await elaborar(usuario);
    rutas["POST /v1/computos/telecom"] = () => json({ detail: "Archivo roto." }, 400);
    await usuario.click(screen.getByRole("button", { name: "Extraer cómputo" }));
    await alertaConTexto();
    await usuario.click(screen.getByRole("button", { name: "Aplicar plan y volver a elaborar" }));
    expect(await screen.findByText("Extraiga de nuevo el computo antes de aplicar el plan.")).toBeInTheDocument();
    expect(llamadas("POST /presupuestos/calcular")).toHaveLength(1);
  });

  describe("rendimientos por declarar (UC-01 3b)", () => {
    function por409(lista: RendimientoPorDeclarar[]) {
      rutas["POST /presupuestos/calcular"] = () =>
        json({ detalle: "Faltan rendimientos.", rendimientos_por_declarar: lista }, 409);
    }

    test("el 409 muestra el bloque con la propuesta, la dispersion y el radio sin seleccion", async () => {
      por409([RENDIMIENTO]);
      const { usuario } = montar();
      await extraerTelecom(usuario);
      await usuario.click(screen.getByRole("button", { name: "Elaborar presupuesto" }));
      expect(await screen.findByRole("heading", { name: "Rendimientos por declarar" })).toBeInTheDocument();
      expect(screen.getByText(/Estas partidas no tienen rendimiento estimado vigente/)).toBeInTheDocument();
      expect(screen.getByText("FIC-T1", { selector: "strong" })).toBeInTheDocument();
      expect(screen.getByText(/rendimiento propuesto 8.5 unidades por dia \(estimado del 2026-01-02\)/)).toBeInTheDocument();
      expect(
        screen.getByText(
          "Dispersion del historico: 3 observaciones (1 medidas, 2 estimadas), media 8.40, rango [7.00, 9.50].",
        ),
      ).toBeInTheDocument();
      const grupo = screen.getByRole("radiogroup", { name: "Tipo declarado del rendimiento de FIC-T1" });
      expect(within(grupo).getByLabelText("estimado")).not.toBeChecked();
      expect(within(grupo).getByLabelText("medido")).not.toBeChecked();
      expect(screen.queryByText("Presupuesto elaborado")).toBeNull();
    });

    test("sin propuesta es un error con el texto de Streamlit y sin boton de registro", async () => {
      por409([RENDIMIENTO_SIN_PROPUESTA]);
      const { usuario } = montar();
      await extraerTelecom(usuario);
      await usuario.click(screen.getByRole("button", { name: "Elaborar presupuesto" }));
      expect(
        await screen.findByText(
          "FIC-T2: la partida no tiene ningun rendimiento registrado que proponer; declarelo con sus condiciones en «Componer una partida».",
        ),
      ).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Registrar y volver a elaborar" })).toBeNull();
    });

    test("registrar sin tipo es un error y no llama a la API", async () => {
      por409([RENDIMIENTO]);
      const { usuario } = montar();
      await extraerTelecom(usuario);
      await usuario.click(screen.getByRole("button", { name: "Elaborar presupuesto" }));
      await usuario.click(await screen.findByRole("button", { name: "Registrar y volver a elaborar" }));
      expect(await screen.findByText("Declare si el rendimiento de FIC-T1 es estimado o medido.")).toBeInTheDocument();
      expect(llamadas("POST /presupuestos/calcular/declarar-rendimiento")).toHaveLength(0);
    });

    test("registrar con tipo declara el rendimiento y vuelve a elaborar", async () => {
      por409([RENDIMIENTO]);
      rutas["POST /presupuestos/calcular/declarar-rendimiento"] = () =>
        json({ codigo_partida: "FIC-T1", valor: "8.5", tipo: "estimado", fecha: hoy(), condiciones: "" });
      const { usuario } = montar();
      await extraerTelecom(usuario);
      await usuario.click(screen.getByRole("button", { name: "Elaborar presupuesto" }));
      const grupo = await screen.findByRole("radiogroup", { name: "Tipo declarado del rendimiento de FIC-T1" });
      await usuario.click(within(grupo).getByLabelText("estimado"));
      rutas["POST /presupuestos/calcular"] = () => json(calculo());
      await usuario.click(screen.getByRole("button", { name: "Registrar y volver a elaborar" }));
      await screen.findByText("Presupuesto elaborado");
      expect(cuerpoJson("POST /presupuestos/calcular/declarar-rendimiento")).toEqual({
        codigo_partida: "FIC-T1",
        tipo: "estimado",
        fecha: hoy(),
      });
      expect(llamadas("POST /presupuestos/calcular")).toHaveLength(2);
      expect(screen.queryByRole("heading", { name: "Rendimientos por declarar" })).toBeNull();
    });

    test("declarar como medido puede dar 422: se muestra el detalle y el bloque sigue", async () => {
      por409([RENDIMIENTO]);
      rutas["POST /presupuestos/calcular/declarar-rendimiento"] = () =>
        json({ detalle: "Un rendimiento medido exige una ejecucion de referencia." }, 422);
      const { usuario } = montar();
      await extraerTelecom(usuario);
      await usuario.click(screen.getByRole("button", { name: "Elaborar presupuesto" }));
      const grupo = await screen.findByRole("radiogroup", { name: "Tipo declarado del rendimiento de FIC-T1" });
      await usuario.click(within(grupo).getByLabelText("medido"));
      await usuario.click(screen.getByRole("button", { name: "Registrar y volver a elaborar" }));
      expect(await alertaConTexto()).toHaveTextContent("Un rendimiento medido exige una ejecucion de referencia.");
      expect(screen.getByRole("heading", { name: "Rendimientos por declarar" })).toBeInTheDocument();
      expect(llamadas("POST /presupuestos/calcular")).toHaveLength(1);
    });

    test("tras registrar una partida la siguiente no hereda el tipo ya declarado", async () => {
      const otra: RendimientoPorDeclarar = { ...RENDIMIENTO, codigo_partida: "FIC-T3" };
      por409([RENDIMIENTO, otra]);
      rutas["POST /presupuestos/calcular/declarar-rendimiento"] = () =>
        json({ codigo_partida: "FIC-T1", valor: "8.5", tipo: "estimado", fecha: hoy(), condiciones: "" });
      const { usuario } = montar();
      await extraerTelecom(usuario);
      await usuario.click(screen.getByRole("button", { name: "Elaborar presupuesto" }));
      const primero = await screen.findByRole("radiogroup", { name: "Tipo declarado del rendimiento de FIC-T1" });
      await usuario.click(within(primero).getByLabelText("estimado"));
      por409([otra]);
      await usuario.click(screen.getAllByRole("button", { name: "Registrar y volver a elaborar" })[0]);
      await waitFor(() => expect(screen.queryByRole("radiogroup", { name: /FIC-T1/ })).toBeNull());
      const segundo = screen.getByRole("radiogroup", { name: "Tipo declarado del rendimiento de FIC-T3" });
      expect(within(segundo).getByLabelText("estimado")).not.toBeChecked();
    });
  });

  test("un 401 al elaborar avisa a la sesion", async () => {
    const { usuario, alExpirar } = montar();
    await extraerTelecom(usuario);
    rutas["POST /presupuestos/calcular"] = () => json({ detalle: "Sesion vencida." }, 401);
    await usuario.click(screen.getByRole("button", { name: "Elaborar presupuesto" }));
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("un 401 al extraer avisa a la sesion", async () => {
    const { usuario, alExpirar } = montar();
    await irATelecom(usuario);
    rutas["POST /v1/computos/telecom"] = () => json({ detalle: "Sesion vencida." }, 401);
    await usuario.upload(campoArchivo(), new File(["a"], "muestra.csv"));
    await usuario.click(screen.getByRole("button", { name: "Extraer cómputo" }));
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });
});
