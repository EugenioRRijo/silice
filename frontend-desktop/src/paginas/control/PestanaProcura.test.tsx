// MP-7, Tarea 24: la pestaña «Procura» de Control de obra y la causa que Valuaciones preelige.
// Contrato de `GET /v1/procura` (Tarea 23): cantidades exactas con punto, fechas aaaa-mm-dd; `POST /v1/procura/compras` y
// `PUT /v1/procura/plazos` reciben las cifras tal como se teclean (coma decimal, punto de miles) y devuelven 204;
// `POST /v1/procura/compras` devuelve 200 `{equivalencia}` (Tarea D2: la conversion del precio del corte, o null).
// Oraculos escritos a mano: 1260.5 se lee «1.260,5»; 2026-11-06, «06/11/2026».
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { MENSAJE_CIFRA } from "../../indicadores/cifraEscrita";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { formulariosSucios, olvidarFormularios } from "../../shell/sucio";
import PaginaControl from "./index";
import type { LineaBase, Valuaciones } from "./logica";
import type { Procura } from "./procura";

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
  descripcion: "versión VIV-001, perspectiva costo, vigente desde 02/11/2026",
  versiones: ["VIV-001"],
  hay_valuaciones: false,
  parametros: [],
};

const VALUACIONES: Valuaciones = {
  tiene_linea_base: true,
  filas: [],
  aviso: "",
  anulables: [],
  corte_por_defecto: null,
  causas: [
    { clave: "compra_tardia", nombre: "Compra tardía" },
    { clave: "clima", nombre: "Lluvia o clima" },
    { clave: "otra", nombre: "Otra" },
  ],
};

const PROCURA: Procura = {
  necesidades: [
    {
      descripcion: "Cemento gris",
      unidad: "saco",
      cantidad: "1260.5",
      partidas: ["OBRA-02", "OBRA-04"],
      se_necesita: "2026-11-06",
      pedir_a_mas_tardar: "2026-11-03",
      plazo: 3,
      pedida: null,
      recibida: null,
    },
    {
      descripcion: "Agua",
      unidad: "m3",
      cantidad: "3.3",
      partidas: ["OBRA-02"],
      se_necesita: "2026-11-06",
      pedir_a_mas_tardar: "2026-11-03",
      plazo: 1,
      pedida: "2026-10-28",
      recibida: "2026-11-09",
    },
  ],
  alertas: [
    { severidad: "ERROR", texto: "Compra tardía: Agua llegó el 09/11/2026 y se necesitaba el 06/11/2026." },
    { severidad: "AVISO", texto: "Pida Cemento gris antes del 03/11/2026." },
  ],
  aviso: null,
  causas_sugeridas: [{ partida: "OBRA-02", causa: "compra_tardia" }],
};

const SIN_LINEA_BASE: Procura = {
  necesidades: [{ ...PROCURA.necesidades[0]!, se_necesita: null, pedir_a_mas_tardar: null }],
  alertas: [],
  aviso: "Declare la línea base para calcular las fechas de compra.",
  causas_sugeridas: [],
};

const MENSAJE_PLAZO = "El plazo de entrega es un número entero de días hábiles, de 0 a 365.";

describe("Control de obra: pestaña Procura (Tarea 24)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let procura: () => Response;
  let compra: () => Response;
  let plazo: () => Response;

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 10, 2, 10, 0));
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    procura = () => json(PROCURA);
    compra = () => json({ equivalencia: null });
    plazo = () => new Response(null, { status: 204 });
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = String(entrada);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/control/linea-base") && metodo === "GET") return json(LINEA_BASE);
      if (url.startsWith("/v1/control/valuaciones") && metodo === "GET") return json(VALUACIONES);
      if (url === "/v1/control/valuaciones") return json({ corte: "2026-11-13", hallazgos: 0, errores: 0 });
      if (url.startsWith("/v1/procura?") && metodo === "GET") return procura();
      if (url === "/v1/procura/compras" && metodo === "POST") return compra();
      if (url === "/v1/procura/plazos" && metodo === "PUT") return plazo();
      return json({ detalle: `ruta inesperada ${metodo} ${url}` }, 500);
    });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    olvidarFormularios();
  });

  function montar() {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: "Vivienda demo",
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

  async function abrirProcura(u: ReturnType<typeof userEvent.setup>) {
    await u.click(await screen.findByRole("tab", { name: "Procura" }));
    return screen.findByRole("table", { name: "Materiales de la obra" });
  }

  function llamadas(ruta: string, metodo: string) {
    return fetchFalso.mock.calls.filter(([u, i]) => String(u) === ruta && (i?.method ?? "GET") === metodo);
  }

  function cuerpoDe(ruta: string, metodo: string) {
    const [llamada] = llamadas(ruta, metodo);
    expect(llamada).toBeDefined();
    return JSON.parse(String(llamada![1]?.body)) as Record<string, unknown>;
  }

  function filaDe(tabla: HTMLElement, insumo: string) {
    const fila = within(tabla)
      .getAllByRole("row")
      .find((f) => within(f).queryAllByRole("cell")[0]?.textContent === insumo);
    expect(fila).toBeDefined();
    return fila!;
  }

  test("«Procura» va después de «Valuaciones»", async () => {
    montar();
    await screen.findByRole("tab", { name: "Procura" });
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual([
      "Línea base",
      "Valuaciones",
      "Procura",
      "Valor ganado",
      "Alertas y reproyección",
      "Recuperación",
    ]);
  });

  test("las demás pestañas siguen pintando lo suyo después de mover los índices", async () => {
    const u = montar();
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    expect(await screen.findByRole("heading", { level: 2, name: /Valuaciones registradas/ })).toBeInTheDocument();
  });

  test("la tabla de necesidades: insumo, cantidad en es-VE, partidas y fechas dd/mm/aaaa, sin title con punto", async () => {
    const u = montar();
    const tabla = await abrirProcura(u);
    expect(within(tabla).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
      "Insumo",
      "Cantidad",
      "Partidas",
      "Se necesita",
      "Pedir a más tardar",
      "Plazo (días hábiles)",
      "Pedida",
      "Recibida",
    ]);
    const cemento = within(filaDe(tabla, "Cemento gris")).getAllByRole("cell");
    expect(cemento.slice(0, 5).map((c) => c.textContent)).toEqual([
      "Cemento gris",
      "1.260,5 saco",
      "OBRA-02, OBRA-04",
      "06/11/2026",
      "03/11/2026",
    ]);
    const agua = within(filaDe(tabla, "Agua")).getAllByRole("cell");
    expect(agua.slice(1, 2).map((c) => c.textContent)).toEqual(["3,3 m3"]);
    expect(agua[6]!.textContent).toBe("28/10/2026");
    expect(agua[7]!.textContent).toBe("09/11/2026");
    // Lo pedido o recibido ya no ofrece «Pedida hoy» ni «Recibida…».
    expect(within(filaDe(tabla, "Agua")).queryByRole("button", { name: /Pedida hoy/ })).toBeNull();
    expect(within(filaDe(tabla, "Agua")).queryByRole("button", { name: /Recibida/ })).toBeNull();
    for (const conTitulo of tabla.querySelectorAll("[title]")) {
      expect(conTitulo.getAttribute("title")).not.toMatch(/[0-9]\.[0-9]/);
    }
  });

  test("las alertas dicen su severidad con texto e ícono, no solo con color", async () => {
    const u = montar();
    await abrirProcura(u);
    expect(screen.getByRole("heading", { level: 2, name: "Alertas de compra" })).toBeInTheDocument();
    const tabla = screen.getByRole("table", { name: "Alertas de compra" });
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(filas.map((f) => within(f).getAllByRole("cell").map((c) => c.textContent))).toEqual([
      ["Error", "Compra tardía: Agua llegó el 09/11/2026 y se necesitaba el 06/11/2026."],
      ["Advertencia", "Pida Cemento gris antes del 03/11/2026."],
    ]);
    for (const fila of filas) expect(within(fila).getAllByRole("cell")[0]!.querySelector("svg")).not.toBeNull();
  });

  test("«Pedida hoy» anota el pedido con la fecha de hoy y lo dice con texto neutro", async () => {
    const u = montar();
    const tabla = await abrirProcura(u);
    const pedidasAntes = llamadas("/v1/procura", "GET").length;
    await u.click(within(tabla).getByRole("button", { name: "Pedida hoy: Cemento gris (saco)" }));
    expect(await screen.findByText("Pedido de Cemento gris anotado con fecha 02/11/2026.")).toBeInTheDocument();
    expect(cuerpoDe("/v1/procura/compras", "POST")).toEqual({
      proyecto: "Vivienda demo",
      descripcion: "Cemento gris",
      unidad: "saco",
      evento: "pedida",
      fecha: "2026-11-02",
    });
    expect(document.querySelector(".cds--inline-notification--success")).toBeNull();
    // Se vuelve a leer la procura (la alerta del cemento se va).
    await waitFor(() =>
      expect(fetchFalso.mock.calls.filter(([url]) => String(url).startsWith("/v1/procura?")).length).toBeGreaterThan(
        pedidasAntes,
      ),
    );
  });

  test("«Recibida…» abre un diálogo con fecha, cantidad y precio unitario que viajan tal como se escriben", async () => {
    const u = montar();
    const tabla = await abrirProcura(u);
    await u.click(within(tabla).getByRole("button", { name: "Recibida…: Cemento gris (saco)" }));
    const dialogo = screen.getByRole("dialog", { name: "Recepción de Cemento gris" });
    const fecha = within(dialogo).getByLabelText("Fecha de llegada");
    expect(fecha).toHaveFocus();
    expect(fecha).toHaveValue("2026-11-02");
    await u.type(within(dialogo).getByLabelText("Cantidad recibida (saco, opcional)"), "1.260,5");
    await u.type(within(dialogo).getByLabelText("Precio unitario (por saco, opcional)"), "1.020,50");
    await u.click(within(dialogo).getByRole("button", { name: "Anotar recepción" }));
    expect(await screen.findByText("Recepción de Cemento gris anotada con fecha 02/11/2026.")).toBeInTheDocument();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(cuerpoDe("/v1/procura/compras", "POST")).toEqual({
      proyecto: "Vivienda demo",
      descripcion: "Cemento gris",
      unidad: "saco",
      evento: "recibida",
      fecha: "2026-11-02",
      cantidad: "1.260,5",
      precio: "1.020,50",
    });
    expect(document.querySelector(".cds--inline-notification--success")).toBeNull();
  });

  // Tarea 25: la casilla «Declararlo precio del corte» de la recepcion deja el precio unitario como precio del corte de
  // la obra desde la fecha de llegada (`declarar_corte` solo viaja si se marco; sin precio no se envia).
  test("con la casilla marcada, el precio de la recepción se declara precio del corte y lo dice", async () => {
    const u = montar();
    const tabla = await abrirProcura(u);
    await u.click(within(tabla).getByRole("button", { name: "Recibida…: Cemento gris (saco)" }));
    const dialogo = screen.getByRole("dialog", { name: "Recepción de Cemento gris" });
    const casilla = within(dialogo).getByRole("checkbox", { name: "Declararlo precio del corte" });
    expect(casilla).not.toBeChecked();
    expect(
      within(dialogo).getByText(
        "Desde la fecha de llegada, Control de obra lo usará para separar el desvío de precio («Precios declarados de insumos»).",
      ),
    ).toBeInTheDocument();
    await u.type(within(dialogo).getByLabelText("Precio unitario (por saco, opcional)"), "20,00");
    await u.click(casilla);
    await u.click(within(dialogo).getByRole("button", { name: "Anotar recepción" }));
    expect(
      await screen.findByText(
        "Recepción de Cemento gris anotada con fecha 02/11/2026. Su precio queda como precio del corte desde esa fecha.",
      ),
    ).toBeInTheDocument();
    expect(cuerpoDe("/v1/procura/compras", "POST")).toEqual({
      proyecto: "Vivienda demo",
      descripcion: "Cemento gris",
      unidad: "saco",
      evento: "recibida",
      fecha: "2026-11-02",
      cantidad: "",
      precio: "20,00",
      declarar_corte: true,
    });
  });

  // Tarea D2: el precio de la recepcion en otra moneda que la obra se convierte con la tasa del BCV de la fecha de
  // llegada; la linea de estado trae la cuenta. 146,00 Bs / 36,50 Bs/USD = 4,00 USD.
  test("si el precio del corte se convirtió, la línea de estado trae la equivalencia", async () => {
    compra = () =>
      json({
        equivalencia: {
          precio_original: "146.00",
          moneda_original: "Bs",
          tasa: "36.50",
          fecha_tasa: "2026-11-02",
          fuente_tasa: "importacion:1",
          convertido: "4",
          moneda: "USD",
          operacion: "÷",
        },
      });
    const u = montar();
    const tabla = await abrirProcura(u);
    await u.click(within(tabla).getByRole("button", { name: "Recibida…: Cemento gris (saco)" }));
    const dialogo = screen.getByRole("dialog", { name: "Recepción de Cemento gris" });
    await u.type(within(dialogo).getByLabelText("Precio unitario (por saco, opcional)"), "146,00");
    await u.click(within(dialogo).getByRole("checkbox", { name: "Declararlo precio del corte" }));
    await u.click(within(dialogo).getByRole("button", { name: "Anotar recepción" }));
    expect(
      await screen.findByText(
        "Recepción de Cemento gris anotada con fecha 02/11/2026. Su precio queda como precio del corte desde esa fecha. Se convirtió con la tasa del BCV: 146,00 Bs ÷ 36,50 Bs/USD (BCV del 02/11/2026) = 4,00 USD",
      ),
    ).toBeInTheDocument();
  });

  test("el precio deja de llamarse «opcional» mientras la casilla está marcada y lo vuelve a ser al desmarcarla", async () => {
    const u = montar();
    const tabla = await abrirProcura(u);
    await u.click(within(tabla).getByRole("button", { name: "Recibida…: Cemento gris (saco)" }));
    const dialogo = screen.getByRole("dialog", { name: "Recepción de Cemento gris" });
    const casilla = within(dialogo).getByRole("checkbox", { name: "Declararlo precio del corte" });
    expect(within(dialogo).getByLabelText("Precio unitario (por saco, opcional)")).toBeInTheDocument();
    await u.click(casilla);
    expect(within(dialogo).getByLabelText("Precio unitario (por saco)")).toBeInTheDocument();
    expect(within(dialogo).queryByLabelText(/Precio unitario.*opcional/)).toBeNull();
    await u.click(casilla);
    expect(within(dialogo).getByLabelText("Precio unitario (por saco, opcional)")).toBeInTheDocument();
  });

  test("con la casilla marcada y sin precio, se pide el precio en su campo y no se envía", async () => {
    const u = montar();
    const tabla = await abrirProcura(u);
    await u.click(within(tabla).getByRole("button", { name: "Recibida…: Cemento gris (saco)" }));
    const dialogo = screen.getByRole("dialog", { name: "Recepción de Cemento gris" });
    await u.click(within(dialogo).getByRole("checkbox", { name: "Declararlo precio del corte" }));
    await u.click(within(dialogo).getByRole("button", { name: "Anotar recepción" }));
    const precio = within(dialogo).getByLabelText("Precio unitario (por saco)");
    expect(
      await within(dialogo).findByText("El precio unitario hace falta para declararlo precio del corte."),
    ).toBeInTheDocument();
    await waitFor(() => expect(precio).toHaveFocus());
    expect(precio).toHaveAttribute("aria-invalid", "true");
    expect(llamadas("/v1/procura/compras", "POST")).toHaveLength(0);
  });

  test("un precio con punto decimal se marca en su campo, recibe el foco y no se envía; Esc cierra y devuelve el foco", async () => {
    const u = montar();
    const tabla = await abrirProcura(u);
    const abrir = within(tabla).getByRole("button", { name: "Recibida…: Cemento gris (saco)" });
    await u.click(abrir);
    const dialogo = screen.getByRole("dialog", { name: "Recepción de Cemento gris" });
    const precio = within(dialogo).getByLabelText("Precio unitario (por saco, opcional)");
    await u.type(precio, "20.5");
    expect(formulariosSucios()).toEqual(["control"]);
    await u.click(within(dialogo).getByRole("button", { name: "Anotar recepción" }));
    expect(await within(dialogo).findByText(MENSAJE_CIFRA)).toBeInTheDocument();
    expect(precio).toHaveFocus();
    expect(precio).toHaveAttribute("aria-invalid", "true");
    expect(llamadas("/v1/procura/compras", "POST")).toHaveLength(0);
    await u.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(formulariosSucios()).toEqual([]);
    expect(abrir).toHaveFocus();
  });

  test("el error de la API sobre la fecha va junto a la fecha, con el foco", async () => {
    compra = () => json({ detalle: "La fecha de la compra no puede ser posterior a hoy." }, 422);
    const u = montar();
    const tabla = await abrirProcura(u);
    await u.click(within(tabla).getByRole("button", { name: "Recibida…: Cemento gris (saco)" }));
    const dialogo = screen.getByRole("dialog", { name: "Recepción de Cemento gris" });
    await u.click(within(dialogo).getByRole("button", { name: "Anotar recepción" }));
    const fecha = within(dialogo).getByLabelText("Fecha de llegada");
    expect(await within(dialogo).findByText("La fecha de la compra no puede ser posterior a hoy.")).toBeInTheDocument();
    await waitFor(() => expect(fecha).toHaveFocus());
    expect(fecha).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  test("el foco queda atrapado en el diálogo: Tab desde el último vuelve al primero", async () => {
    const u = montar();
    const tabla = await abrirProcura(u);
    await u.click(within(tabla).getByRole("button", { name: "Recibida…: Cemento gris (saco)" }));
    const dialogo = screen.getByRole("dialog", { name: "Recepción de Cemento gris" });
    within(dialogo).getByRole("button", { name: "Anotar recepción" }).focus();
    await u.tab();
    expect(within(dialogo).getByLabelText("Fecha de llegada")).toHaveFocus();
    await u.tab({ shift: true });
    expect(within(dialogo).getByRole("button", { name: "Anotar recepción" })).toHaveFocus();
  });

  test("el plazo se cambia en su diálogo y viaja tal como se escribe", async () => {
    const u = montar();
    const tabla = await abrirProcura(u);
    const cemento = within(filaDe(tabla, "Cemento gris")).getAllByRole("cell");
    expect(cemento[5]!.textContent).toMatch(/^3/);
    await u.click(within(tabla).getByRole("button", { name: "Cambiar el plazo de Cemento gris (saco)" }));
    const dialogo = screen.getByRole("dialog", { name: "Plazo de entrega de Cemento gris" });
    const dias = within(dialogo).getByLabelText("Días hábiles de entrega");
    expect(dias).toHaveFocus();
    expect(dias).toHaveValue("3");
    await u.clear(dias);
    await u.type(dias, "5");
    expect(formulariosSucios()).toEqual(["control"]);
    await u.click(within(dialogo).getByRole("button", { name: "Guardar plazo" }));
    expect(await screen.findByText("Plazo de Cemento gris: 5 días hábiles.")).toBeInTheDocument();
    expect(cuerpoDe("/v1/procura/plazos", "PUT")).toEqual({
      proyecto: "Vivienda demo",
      descripcion: "Cemento gris",
      unidad: "saco",
      dias: "5",
    });
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(formulariosSucios()).toEqual([]);
  });

  test("un plazo que la API rechaza se marca en el campo con su mensaje y el foco", async () => {
    plazo = () => json({ detalle: MENSAJE_PLAZO }, 422);
    const u = montar();
    const tabla = await abrirProcura(u);
    await u.click(within(tabla).getByRole("button", { name: "Cambiar el plazo de Cemento gris (saco)" }));
    const dialogo = screen.getByRole("dialog", { name: "Plazo de entrega de Cemento gris" });
    const dias = within(dialogo).getByLabelText("Días hábiles de entrega");
    await u.clear(dias);
    await u.type(dias, "2,5");
    await u.click(within(dialogo).getByRole("button", { name: "Guardar plazo" }));
    expect(await within(dialogo).findByText(MENSAJE_PLAZO)).toBeInTheDocument();
    await waitFor(() => expect(dias).toHaveFocus());
    expect(dias).toHaveAttribute("aria-invalid", "true");
  });

  test("sin línea base lo dice, no hay fechas y no hay alertas", async () => {
    procura = () => json(SIN_LINEA_BASE);
    const u = montar();
    const tabla = await abrirProcura(u);
    expect(screen.getByText("Declare la línea base para calcular las fechas de compra.")).toBeInTheDocument();
    const cemento = within(filaDe(tabla, "Cemento gris")).getAllByRole("cell");
    expect(cemento.slice(3, 5).map((c) => c.textContent)).toEqual(["Sin fecha", "Sin fecha"]);
    expect(screen.getByText("No hay compras por pedir ni compras tardías.")).toBeInTheDocument();
    expect(screen.queryByRole("table", { name: "Alertas de compra" })).toBeNull();
  });
});

describe("Valuaciones: la causa que sugiere la procura (Tarea 24)", () => {
  const fetchFalso = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = String(entrada);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/control/linea-base") && metodo === "GET") return json(LINEA_BASE);
      if (url.startsWith("/v1/control/valuaciones") && metodo === "GET") return json(VALUACIONES);
      if (url === "/v1/control/valuaciones") return json({ corte: "2026-11-13", hallazgos: 0, errores: 0 });
      if (url.startsWith("/v1/procura?") && metodo === "GET") return json(PROCURA);
      return json({ detalle: `ruta inesperada ${metodo} ${url}` }, 500);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    olvidarFormularios();
  });

  function montar() {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: "Vivienda demo",
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
    return (JSON.parse(String(llamada![1]?.body)) as { lineas: { partida: string; causa: string | null }[] }).lineas;
  }

  async function abrirValuaciones(u: ReturnType<typeof userEvent.setup>) {
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    await screen.findByRole("combobox", { name: "Causa del retraso 1" });
  }

  test("OBRA-02 llega con «Compra tardía» elegida y lo dice; otra partida, sin causa", async () => {
    const u = montar();
    await abrirValuaciones(u);
    await u.type(screen.getByLabelText("Período hasta"), "2026-11-13");
    await waitFor(() =>
      expect(fetchFalso.mock.calls.some(([url]) => String(url).startsWith("/v1/procura?") && String(url).includes("corte=2026-11-13"))).toBe(
        true,
      ),
    );
    await u.type(screen.getByLabelText("Partida 1"), "OBRA-02");
    const causa = screen.getByRole("combobox", { name: "Causa del retraso 1" });
    await waitFor(() => expect(causa).toHaveValue("compra_tardia"));
    expect(screen.getByText("Sugerida por la procura: un material de esta partida llegó tarde. Puede cambiarla.")).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Agregar línea" }));
    await u.type(screen.getByLabelText("Partida 2"), "OBRA-01");
    expect(screen.getByRole("combobox", { name: "Causa del retraso 2" })).toHaveValue("");
    await u.type(screen.getByLabelText("Cantidad 1"), "5");
    await u.type(screen.getByLabelText("Cantidad 2"), "1");
    await u.click(screen.getByRole("button", { name: "Registrar y controlar" }));
    await screen.findByText(/Valuación registrada/);
    expect(lineasEnviadas().map((l) => [l.partida, l.causa])).toEqual([
      ["OBRA-02", "compra_tardia"],
      ["OBRA-01", null],
    ]);
  });

  test("al cambiar el «hasta» la causa sugerida se queda mientras la procura recarga", async () => {
    const u = montar();
    await abrirValuaciones(u);
    await u.type(screen.getByLabelText("Partida 1"), "OBRA-02");
    const causa = screen.getByRole("combobox", { name: "Causa del retraso 1" });
    await waitFor(() => expect(causa).toHaveValue("compra_tardia"));
    // De aquí en adelante la procura no contesta: la lista nueva nunca llega.
    const respondeBien = fetchFalso.getMockImplementation()!;
    fetchFalso.mockImplementation((entrada, init) =>
      String(entrada).startsWith("/v1/procura?") ? new Promise<Response>(() => undefined) : respondeBien(entrada, init),
    );
    await u.type(screen.getByLabelText("Período hasta"), "2026-11-13");
    await waitFor(() =>
      expect(fetchFalso.mock.calls.some(([url]) => String(url).includes("corte=2026-11-13"))).toBe(true),
    );
    expect(causa).toHaveValue("compra_tardia");
    expect(screen.getByText("Sugerida por la procura: un material de esta partida llegó tarde. Puede cambiarla.")).toBeInTheDocument();
  });

  test("la persona puede cambiar la causa sugerida, también a «Sin causa», y vale lo que eligió", async () => {
    const u = montar();
    await abrirValuaciones(u);
    await u.type(screen.getByLabelText("Partida 1"), "OBRA-02");
    const causa = screen.getByRole("combobox", { name: "Causa del retraso 1" });
    await waitFor(() => expect(causa).toHaveValue("compra_tardia"));
    await u.selectOptions(causa, "Lluvia o clima");
    expect(causa).toHaveValue("clima");
    expect(screen.queryByText(/Sugerida por la procura/)).toBeNull();
    await u.click(screen.getByRole("button", { name: "Agregar línea" }));
    await u.type(screen.getByLabelText("Partida 2"), "OBRA-02");
    const segunda = screen.getByRole("combobox", { name: "Causa del retraso 2" });
    await waitFor(() => expect(segunda).toHaveValue("compra_tardia"));
    await u.selectOptions(segunda, "Sin causa");
    expect(segunda).toHaveValue("");
    await u.type(screen.getByLabelText("Cantidad 1"), "5");
    await u.type(screen.getByLabelText("Cantidad 2"), "1");
    await u.click(screen.getByRole("button", { name: "Registrar y controlar" }));
    await screen.findByText(/Valuación registrada/);
    expect(lineasEnviadas().map((l) => l.causa)).toEqual(["clima", null]);
  });
});
