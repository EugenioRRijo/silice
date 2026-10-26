import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import { alertaConTexto } from "../../test/ayudas";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { formulariosSucios, olvidarFormularios } from "../../shell/sucio";
import PaginaMercado from "./index";

// Pagina «Estudio de mercado» (plan de montar un presupuesto, Tarea 15). Las respuestas son las del contrato de la
// Tarea 14 (`api/rutas/mercado.py`: montos como texto con punto), simuladas; insumos, partidas, fuentes y precios
// ficticios. Oraculos escritos a mano: las cifras de [100, 120, 130, 150, 200] de la Tarea 13 (minimo 100, primer
// cuartil 120, mediana 130, promedio 140, maximo 200).

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto"],
  modo_entrega: false,
};

const INSUMOS = [
  { codigo: "CEM-GRIS", descripcion: "Cemento gris ficticio, saco de 42,5 kg", tipo: "material", unidad: "saco", precio_vigente: "18.00" },
  { codigo: "ARE-LAV", descripcion: "Arena lavada ficticia", tipo: "material", unidad: "m3", precio_vigente: "25.00" },
];

const PARTIDAS = {
  rotulo: "Partidas del catálogo",
  resultados: [
    {
      clave: "partida:OBRA-04",
      codigo: "OBRA-04",
      descripcion: "Friso liso ficticio en paredes",
      unidad: "m2",
      dominio: "civil",
      tiene_composicion: true,
    },
  ],
  hay_mas: false,
};

function observacion(id: number, precio: string, fuente: string, fecha: string, extra: Record<string, unknown> = {}) {
  return {
    id,
    fuente_tipo: "proveedor",
    fuente,
    fecha,
    moneda: "Bs",
    precio,
    nota: "",
    responsable: "ana",
    cuenta: true,
    ...extra,
  };
}

const ESTUDIO_COMPRA = {
  lado: "compra",
  codigo: "CEM-GRIS",
  moneda: "Bs",
  estadisticas: {
    n: 5,
    minimo: "100.00",
    q1: "120.00",
    mediana: "130.00",
    promedio: "140.00",
    maximo: "200.00",
    ids: [1, 2, 3, 4, 5],
    otras_monedas: 1,
    dias: 90,
  },
  propuesta: { precio: "130.00", razon: "Mediana de 5 observaciones; la más barata vista: 100,00 Bs." },
  piso: null,
  precio_unitario: null,
  observaciones: [
    observacion(1, "100.00", "Ferretería Demo, C.A.", "2026-10-20"),
    observacion(2, "120.00", "Materiales Ficticios del Centro", "2026-10-18", { fuente_tipo: "cotizacion" }),
    observacion(3, "130.00", "Depósito Ejemplo", "2026-10-15"),
    observacion(4, "150.00", "Ferretería Demo, C.A.", "2026-10-02", { nota: "Precio de contado" }),
    observacion(5, "200.00", "Distribuidora Inventada", "2026-09-30"),
    observacion(6, "9.50", "Proveedor en divisas ficticio", "2026-10-01", { moneda: "USD", cuenta: false }),
  ],
};

const ESTUDIO_COBRO = {
  lado: "cobro",
  codigo: "OBRA-04",
  moneda: "Bs",
  estadisticas: {
    n: 4,
    minimo: "1900.00",
    q1: "1950.00",
    mediana: "2000.00",
    promedio: "2012.50",
    maximo: "2200.00",
    ids: [11, 12, 13, 14],
    otras_monedas: 0,
    dias: 90,
  },
  propuesta: { precio: "2010.50", razon: "La competencia cobra menos que su costo: se propone su costo." },
  piso: "2010.50",
  precio_unitario: "2074.44",
  observaciones: [
    observacion(11, "1900.00", "Constructora Competidora Demo", "2026-10-10", { fuente_tipo: "competidor" }),
    observacion(12, "1950.00", "Licitación ficticia", "2026-10-08", { fuente_tipo: "competidor" }),
    observacion(13, "2050.00", "Constructora Ejemplo", "2026-09-20", { fuente_tipo: "competidor" }),
    observacion(14, "2200.00", "Contratista Demo B", "2026-09-01", { fuente_tipo: "competidor" }),
  ],
};

type Respuesta = Response | (() => Response);
interface Ruta {
  metodo: string;
  ruta: RegExp;
  respuesta: Respuesta;
}

const fetchFalso = vi.fn<typeof fetch>();
let rutas: Ruta[];

function responder(metodo: string, ruta: RegExp, respuesta: Respuesta) {
  rutas.unshift({ metodo, ruta, respuesta }); // la ultima registrada manda
}

function llamadas(metodo: string, ruta: RegExp): { url: string; cuerpo: unknown }[] {
  return fetchFalso.mock.calls
    .filter(([url, init]) => (init?.method ?? "GET") === metodo && ruta.test(String(url)))
    .map(([url, init]) => ({ url: String(url), cuerpo: init?.body ? JSON.parse(String(init.body)) : undefined }));
}

function montar(extra: Partial<Aplicacion> = {}) {
  const valor: Aplicacion = {
    sesion: SESION,
    proyecto: null,
    caso: { nombre: "clinica", ruta_relativa: "data/clinica.db" },
    recargarProyectos: vi.fn(),
    alExpirar: vi.fn(),
    ...extra,
  };
  render(
    <ContextoAplicacion.Provider value={valor}>
      <MemoryRouter>
        <PaginaMercado />
      </MemoryRouter>
    </ContextoAplicacion.Provider>,
  );
  return valor;
}

async function elegirInsumo(u: ReturnType<typeof userEvent.setup>) {
  await u.type(screen.getByRole("combobox", { name: "Insumo" }), "cemento");
  await u.click(await screen.findByRole("option", { name: /Cemento gris ficticio/ }));
  await screen.findByRole("heading", { name: /Cifras de los últimos 90 días/ });
}

async function elegirPartida(u: ReturnType<typeof userEvent.setup>) {
  await u.click(screen.getByRole("tab", { name: "Lo que cobramos" }));
  await u.type(screen.getByRole("combobox", { name: "Partida" }), "friso");
  await u.click(await screen.findByRole("option", { name: /Friso liso ficticio/ }));
  await screen.findByRole("heading", { name: /Cifras de los últimos 90 días/ });
}

const campoPrecio = () => screen.getByRole("textbox", { name: "Su precio" });
const cifras = () => screen.getByRole("region", { name: /Cifras de los últimos 90 días/ });

describe("Estudio de mercado", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    rutas = [];
    responder("GET", /^\/insumos$/, () => json(INSUMOS));
    responder("GET", /^\/v1\/buscar\/partidas\?/, () => json(PARTIDAS));
    responder("GET", /^\/v1\/mercado\/compra\/CEM-GRIS\?/, () => json(ESTUDIO_COMPRA));
    responder("GET", /^\/v1\/mercado\/cobro\/OBRA-04\?/, () => json(ESTUDIO_COBRO));
    responder("GET", /^\/v1\/mercado\/compra\/CEM-GRIS\/afectados$/, () => json({ apus: ["OBRA-02", "OBRA-04"] }));
    responder("POST", /^\/v1\/mercado\/compra\/CEM-GRIS\/usar$/, () => json({ lista: "Lista de la carpeta al 26/10/2026" }));
    responder("POST", /^\/v1\/mercado\/cobro\/OBRA-04\/usar$/, () =>
      json({ codigo: "OBRA-04", precio: "1980.00", moneda: "Bs" }),
    );
    fetchFalso.mockImplementation(async (url, init) => {
      const metodo = init?.method ?? "GET";
      const ruta = rutas.find((r) => r.metodo === metodo && r.ruta.test(String(url)));
      if (!ruta) return json({ detail: `Ruta no simulada: ${metodo} ${String(url)}` }, 404);
      return typeof ruta.respuesta === "function" ? ruta.respuesta() : ruta.respuesta;
    });
  });
  afterEach(() => {
    olvidarFormularios();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  test("un solo h1, las dos pestañas y, sin elegir nada, qué hacer", () => {
    montar();
    expect(screen.getAllByRole("heading", { level: 1 }).map((h) => h.textContent)).toEqual(["Estudio de mercado"]);
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual(["Lo que compramos", "Lo que cobramos"]);
    expect(screen.getByText("Elija un insumo para ver sus precios en el mercado")).toBeInTheDocument();
  });

  test("las seis cifras del mercado en es-VE, cada monto con las observaciones de las que sale", async () => {
    const u = userEvent.setup();
    montar();
    await elegirInsumo(u);
    expect(llamadas("GET", /\/v1\/mercado\/compra\//)[0].url).toBe("/v1/mercado/compra/CEM-GRIS?dias=90");
    const franja = cifras();
    const pares = within(franja)
      .getAllByRole("term")
      .map((t) => [t.textContent, t.nextElementSibling?.textContent]);
    expect(pares).toEqual([
      ["Observaciones", "5"],
      ["Mínimo", "100,00 Bs"],
      ["Primer cuartil", "120,00 Bs"],
      ["Mediana", "130,00 Bs"],
      ["Promedio", "140,00 Bs"],
      ["Máximo", "200,00 Bs"],
    ]);
    // El exacto de la API queda a la vista de quien lo pida (title), formateado una sola vez.
    expect(within(franja).getByText("140,00")).toHaveAttribute("title", "140.00");
    expect(within(franja).getAllByText("de 5 observaciones")).toHaveLength(5);
    expect(within(franja).getByText("1 observación en otra moneda no entra en las cifras.")).toBeInTheDocument();
    // La propuesta de compra (la mediana) con su razon; el campo de precio, prellenado como se escribe.
    expect(screen.getByText("Mediana de 5 observaciones; la más barata vista: 100,00 Bs.")).toBeInTheDocument();
    expect(campoPrecio()).toHaveValue("130,00");
    // La tabla de observaciones: fecha dd/mm/aaaa, precio en es-VE y la de otra moneda dicha, no escondida.
    const tabla = screen.getByRole("table", { name: "Observaciones de los últimos 90 días" });
    expect(within(tabla).getByText("20/10/2026")).toBeInTheDocument();
    expect(within(tabla).getByText("Materiales Ficticios del Centro")).toBeInTheDocument();
    expect(within(tabla).getByText("Cotización")).toBeInTheDocument();
    expect(within(tabla).getByText("Precio de contado")).toBeInTheDocument();
    expect(within(tabla).getByText("9,50 USD")).toBeInTheDocument();
    expect(within(tabla).getByText("No: está en USD")).toBeInTheDocument();
    expect(tabla).not.toHaveTextContent("2026-10-20");
  });

  test("cobro: su costo (piso), el precio con utilidad y la razón cuando la competencia cobra menos que su costo", async () => {
    const u = userEvent.setup();
    montar({ proyecto: "VIV-001", nombreProyecto: "Vivienda unifamiliar 80 m²" });
    await elegirPartida(u);
    // El piso sale con los parametros de la obra abierta.
    expect(llamadas("GET", /\/v1\/mercado\/cobro\//)[0].url).toBe("/v1/mercado/cobro/OBRA-04?dias=90&proyecto=VIV-001");
    const costo = screen.getByRole("region", { name: "Su costo" });
    const pares = within(costo)
      .getAllByRole("term")
      .map((t) => [t.textContent, t.nextElementSibling?.textContent]);
    expect(pares).toEqual([
      ["Su costo (piso)", "2.010,50 Bs"],
      ["Precio con utilidad", "2.074,44 Bs"],
    ]);
    expect(within(costo).getByText(/Vivienda unifamiliar 80 m²/)).toBeInTheDocument();
    const razon = screen.getByText("La competencia cobra menos que su costo: se propone su costo.");
    expect(razon).toBeInTheDocument();
    // El aviso no va solo con color: lleva su icono con nombre accesible.
    expect(within(razon.closest("p")!).getByRole("img", { name: "Aviso" })).toBeInTheDocument();
    expect(campoPrecio()).toHaveValue("2.010,50");
  });

  test("compra: «Usar este precio» primero dice qué partidas cambiarán y solo tras «Confirmar» guarda", async () => {
    const u = userEvent.setup();
    montar();
    await elegirInsumo(u);
    await u.click(screen.getByRole("button", { name: "Usar este precio" }));
    const confirmar = await screen.findByRole("button", { name: "Confirmar" });
    expect(screen.getByText("Cambiará el precio en OBRA-02 y OBRA-04.")).toBeInTheDocument();
    expect(llamadas("POST", /\/usar$/)).toEqual([]);
    // El foco va a la pregunta, para que se lea antes de confirmar.
    expect(screen.getByText("Cambiará el precio en OBRA-02 y OBRA-04.").closest("[tabindex='-1']")).toHaveFocus();
    await u.click(confirmar);
    await screen.findByText("Precio guardado en «Lista de la carpeta al 26/10/2026».");
    expect(llamadas("POST", /\/usar$/)).toEqual([
      { url: "/v1/mercado/compra/CEM-GRIS/usar", cuerpo: { precio: "130,00", observacion_id: null } },
    ]);
    expect(screen.queryByRole("button", { name: "Confirmar" })).not.toBeInTheDocument();
  });

  test("compra: «Cancelar» no guarda y devuelve el foco a «Usar este precio»", async () => {
    const u = userEvent.setup();
    montar();
    await elegirInsumo(u);
    await u.click(screen.getByRole("button", { name: "Usar este precio" }));
    await u.click(await screen.findByRole("button", { name: "Cancelar" }));
    expect(screen.queryByText("Cambiará el precio en OBRA-02 y OBRA-04.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Usar este precio" })).toHaveFocus();
    expect(llamadas("POST", /\/usar$/)).toEqual([]);
  });

  test("compra: la observación elegida como respaldo viaja con el precio", async () => {
    const u = userEvent.setup();
    montar();
    await elegirInsumo(u);
    await u.selectOptions(screen.getByRole("combobox", { name: "Observación que respalda el precio" }), "3");
    await u.click(screen.getByRole("button", { name: "Usar este precio" }));
    await u.click(await screen.findByRole("button", { name: "Confirmar" }));
    await screen.findByText(/Precio guardado/);
    expect(llamadas("POST", /\/usar$/)[0].cuerpo).toEqual({ precio: "130,00", observacion_id: 3 });
  });

  test("cobro: el precio se envía tal como se escribió («1.980,00») con las observaciones de las cifras", async () => {
    const u = userEvent.setup();
    montar();
    await elegirPartida(u);
    await u.clear(campoPrecio());
    await u.type(campoPrecio(), "1.980,00");
    await u.click(screen.getByRole("button", { name: "Usar este precio" }));
    await screen.findByText("Precio objetivo guardado: 1.980,00 Bs. La Hoja lo mostrará junto al precio del APU.");
    expect(llamadas("POST", /\/usar$/)).toEqual([
      { url: "/v1/mercado/cobro/OBRA-04/usar", cuerpo: { precio: "1.980,00", observaciones: [11, 12, 13, 14] } },
    ]);
    // En cobro no hay partidas que cambien: no se pregunta.
    expect(llamadas("GET", /\/afectados$/)).toEqual([]);
  });

  test("un 422 de la API se muestra en el campo de precio, con su mensaje tal cual", async () => {
    const u = userEvent.setup();
    responder("POST", /^\/v1\/mercado\/cobro\/OBRA-04\/usar$/, () =>
      json({ detail: "El precio objetivo admite hasta 2 decimales (céntimos)." }, 422),
    );
    montar();
    await elegirPartida(u);
    await u.clear(campoPrecio());
    await u.type(campoPrecio(), "1.980,005");
    await u.click(screen.getByRole("button", { name: "Usar este precio" }));
    await waitFor(() => expect(campoPrecio()).toHaveAttribute("aria-invalid", "true"));
    expect(campoPrecio()).toHaveAccessibleDescription("El precio objetivo admite hasta 2 decimales (céntimos).");
    expect(llamadas("POST", /\/usar$/)[0].cuerpo).toEqual({ precio: "1.980,005", observaciones: [11, 12, 13, 14] });
    // Al corregir, el error se va.
    await u.type(campoPrecio(), "{Backspace}");
    expect(campoPrecio()).not.toHaveAttribute("aria-invalid", "true");
  });

  test("un precio con punto decimal se corrige en el campo sin llamar a la API", async () => {
    const u = userEvent.setup();
    montar();
    await elegirPartida(u);
    await u.clear(campoPrecio());
    await u.type(campoPrecio(), "1980.5");
    await u.click(screen.getByRole("button", { name: "Usar este precio" }));
    expect(campoPrecio()).toHaveAttribute("aria-invalid", "true");
    expect(campoPrecio()).toHaveAccessibleDescription(
      "Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56.",
    );
    expect(llamadas("POST", /\/usar$/)).toEqual([]);
  });

  test("un precio cambiado y sin usar deja la pantalla sucia (la confirmación única al salir)", async () => {
    const u = userEvent.setup();
    montar();
    await elegirInsumo(u);
    expect(formulariosSucios()).toEqual([]);
    await u.type(campoPrecio(), "5");
    expect(formulariosSucios()).toEqual(["mercado"]);
    await u.click(screen.getByRole("button", { name: "Usar este precio" }));
    await u.click(await screen.findByRole("button", { name: "Confirmar" }));
    await screen.findByText(/Precio guardado/);
    expect(formulariosSucios()).toEqual([]);
  });

  test("anotar una observación envía el precio tal como se escribió y vuelve a leer las cifras", async () => {
    const u = userEvent.setup();
    responder("POST", /^\/v1\/mercado\/observaciones$/, () => json({ id: 7 }, 201));
    montar();
    await elegirInsumo(u);
    const formulario = screen.getByRole("form", { name: "Anotar una observación" });
    await u.selectOptions(within(formulario).getByRole("combobox", { name: "De dónde sale" }), "cotizacion");
    await u.type(within(formulario).getByRole("textbox", { name: "Fuente" }), "Ferretería Demo, C.A.");
    fireEvent.change(within(formulario).getByLabelText("Fecha"), { target: { value: "2026-10-21" } });
    await u.type(within(formulario).getByRole("textbox", { name: "Precio (Bs)" }), "1.234,50");
    await u.type(within(formulario).getByRole("textbox", { name: "Nota (opcional)" }), "Pago a 30 días");
    expect(formulariosSucios()).toEqual(["mercado"]);
    await u.click(within(formulario).getByRole("button", { name: "Anotar observación" }));
    await screen.findByText("Observación n.º 7 anotada.");
    expect(llamadas("POST", /\/v1\/mercado\/observaciones$/)).toEqual([
      {
        url: "/v1/mercado/observaciones",
        cuerpo: {
          lado: "compra",
          codigo: "CEM-GRIS",
          fuente_tipo: "cotizacion",
          fuente: "Ferretería Demo, C.A.",
          fecha: "2026-10-21",
          precio: "1.234,50",
          nota: "Pago a 30 días",
        },
      },
    ]);
    expect(llamadas("GET", /\/v1\/mercado\/compra\/CEM-GRIS\?/)).toHaveLength(2);
    expect(within(formulario).getByRole("textbox", { name: "Fuente" })).toHaveValue("");
    expect(formulariosSucios()).toEqual([]);
  });

  test("anular una observación pide confirmarlo y vuelve a leer las cifras", async () => {
    const u = userEvent.setup();
    responder("POST", /^\/v1\/mercado\/observaciones\/5\/anular$/, () => json({ id: 5, anulada_por: 8 }));
    montar();
    await elegirInsumo(u);
    await u.click(screen.getByRole("button", { name: "Anular la observación n.º 5" }));
    const pregunta = screen.getByText(/¿Anular la observación n\.º 5 \(Distribuidora Inventada, 30\/09\/2026, 200,00 Bs\)\?/);
    expect(pregunta.closest("[tabindex='-1']")).toHaveFocus();
    expect(llamadas("POST", /\/anular$/)).toEqual([]);
    await u.click(screen.getByRole("button", { name: "Anular la observación" }));
    await screen.findByText("Observación n.º 5 anulada. Queda constancia de quién y cuándo.");
    expect(llamadas("POST", /\/anular$/).map((l) => l.url)).toEqual(["/v1/mercado/observaciones/5/anular"]);
    expect(llamadas("GET", /\/v1\/mercado\/compra\/CEM-GRIS\?/)).toHaveLength(2);
  });

  test("cambiar la ventana de días vuelve a pedir el estudio con esos días", async () => {
    const u = userEvent.setup();
    responder("GET", /^\/v1\/mercado\/compra\/CEM-GRIS\?dias=30$/, () =>
      json({ ...ESTUDIO_COMPRA, estadisticas: { ...ESTUDIO_COMPRA.estadisticas, dias: 30 } }),
    );
    montar();
    await elegirInsumo(u);
    const dias = screen.getByRole("textbox", { name: "Días hacia atrás" });
    await u.clear(dias);
    await u.type(dias, "30");
    await u.click(screen.getByRole("button", { name: "Ver estos días" }));
    await screen.findByRole("heading", { name: /Cifras de los últimos 30 días/ });
    await u.clear(dias);
    await u.type(dias, "0");
    await u.click(screen.getByRole("button", { name: "Ver estos días" }));
    expect(dias).toHaveAttribute("aria-invalid", "true");
    expect(llamadas("GET", /\/v1\/mercado\/compra\/CEM-GRIS\?/).map((l) => l.url)).toEqual([
      "/v1/mercado/compra/CEM-GRIS?dias=90",
      "/v1/mercado/compra/CEM-GRIS?dias=30",
    ]);
  });

  test("sin observaciones en la ventana lo dice y enseña qué hacer; el campo de precio queda vacío", async () => {
    const u = userEvent.setup();
    responder("GET", /^\/v1\/mercado\/compra\/CEM-GRIS\?/, () =>
      json({
        ...ESTUDIO_COMPRA,
        estadisticas: { n: 0, minimo: null, q1: null, mediana: null, promedio: null, maximo: null, ids: [], otras_monedas: 0, dias: 90 },
        propuesta: { precio: null, razon: "Sin observaciones en los últimos 90 días." },
        observaciones: [],
      }),
    );
    montar();
    await elegirInsumo(u);
    expect(screen.getByText("Sin observaciones en los últimos 90 días.")).toBeInTheDocument();
    expect(screen.getByText(/Anote el primer precio que vea/)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(campoPrecio()).toHaveValue("");
  });

  test("un 409 al leer el estudio se dice con el detalle de la API", async () => {
    const u = userEvent.setup();
    responder("GET", /^\/v1\/mercado\/compra\/CEM-GRIS\?/, () =>
      json(
        { detail: "Esta carpeta de trabajo aún no tiene moneda: declárela o cree su lista para armar antes de estudiar el mercado." },
        409,
      ),
    );
    montar();
    await u.type(screen.getByRole("combobox", { name: "Insumo" }), "cemento");
    await u.click(await screen.findByRole("option", { name: /Cemento gris ficticio/ }));
    const alerta = await alertaConTexto();
    expect(alerta).toHaveTextContent("No se pudo leer el estudio de mercado");
    expect(alerta).toHaveTextContent("Esta carpeta de trabajo aún no tiene moneda");
  });
});
