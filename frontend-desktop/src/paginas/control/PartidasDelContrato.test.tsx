// AC2 (pedido de Eugenio, 2026-10-21): «Partida» de una valuación y «Partida (opcional)» de un costo ofrecen las
// partidas de la versión de la línea base (GET /v1/control/partidas). Oráculo a mano: OB-S2 (control_ob_s2.py) presupuesta
// A, B y C; OB-D se valúa en su memoria pero no está presupuestada.
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaControl from "./index";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["control_de_obra"],
  modo_entrega: false,
};

const LINEA_BASE = {
  tiene_linea_base: true,
  descripcion: "versión OB-001, perspectiva costo, vigente desde 02/11/2026",
  versiones: ["OB-001"],
  hay_valuaciones: false,
  parametros: [],
};

const VALUACIONES = {
  tiene_linea_base: true,
  filas: [],
  impuestos: { subtotal: "0.00", iva: "0.00", total: "0.00", alicuota: "0.16", fuente_alicuota: "Decreto ficticio" },
  perspectiva: "costo",
  aviso: "",
  anulables: [],
  corte_por_defecto: "2026-11-13",
  causas: [],
};

const PARTIDAS = {
  version: "OB-001",
  aviso: "",
  partidas: [
    { codigo: "OB-A", descripcion: "Excavacion de zanja", unidad: "m3" },
    { codigo: "OB-B", descripcion: "Tuberia de drenaje", unidad: "m" },
    { codigo: "OB-C", descripcion: "Relleno compactado", unidad: "m3" },
  ],
};

describe("Control: autocompletado de la partida (AC2)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let partidas: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    partidas = () => json(PARTIDAS);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://x");
      const metodo = init?.method ?? "GET";
      if (url.pathname === "/v1/control/linea-base" && metodo === "GET") return json(LINEA_BASE);
      if (url.pathname === "/v1/control/valuaciones" && metodo === "GET") return json(VALUACIONES);
      if (url.pathname === "/v1/control/partidas" && metodo === "GET") return partidas();
      if (url.pathname === "/v1/control/valuaciones") return json({ corte: "2026-11-20", hallazgos: 0, errores: 0 });
      if (url.pathname === "/v1/control/costos") return json({});
      return json({ detalle: `ruta inesperada ${metodo} ${url.pathname}` }, 500);
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  async function montarEnValuaciones() {
    const aplicacion: Aplicacion = {
      sesion: SESION,
      proyecto: "OB-S2",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    render(
      <ContextoAplicacion.Provider value={aplicacion}>
        <PaginaControl />
      </ContextoAplicacion.Provider>,
    );
    const u = userEvent.setup();
    await u.click(await screen.findByRole("tab", { name: "Valuaciones" }));
    await screen.findByLabelText("Partida 1");
    return u;
  }

  function envio(ruta: string) {
    const llamada = fetchFalso.mock.calls.find(([u, i]) => new URL(String(u), "http://x").pathname === ruta && i?.method === "POST");
    return llamada ? (JSON.parse(String(llamada[1]?.body)) as Record<string, unknown>) : undefined;
  }

  test("pide las partidas del contrato de esta obra una sola vez", async () => {
    await montarEnValuaciones();
    await waitFor(() => {
      const pedidas = fetchFalso.mock.calls.filter(([u]) => String(u).startsWith("/v1/control/partidas"));
      expect(pedidas.map(([u]) => String(u))).toEqual(["/v1/control/partidas?proyecto=OB-S2"]);
    });
  });

  test("«Partida 1» ofrece las del contrato con código, descripción y unidad, y elegir con el teclado llena el código", async () => {
    const u = await montarEnValuaciones();
    const campo = screen.getByLabelText("Partida 1");
    expect(campo).toHaveAttribute("role", "combobox");
    await u.type(campo, "zanja");
    const opcion = await screen.findByRole("option", { name: /Excavacion de zanja/ });
    expect(opcion).toHaveTextContent("OB-A");
    expect(opcion).toHaveTextContent("m3");
    expect(screen.queryByRole("option", { name: /Tuberia/ })).toBeNull();
    await u.keyboard("{ArrowDown}{Enter}");
    expect(campo).toHaveValue("OB-A");
    // La descripción y la unidad de lo elegido quedan junto al campo para medir en la unidad correcta.
    expect(await screen.findByText(/Excavacion de zanja · m3/)).toBeInTheDocument();
  });

  test("lo elegido se registra con su código", async () => {
    const u = await montarEnValuaciones();
    await u.type(screen.getByLabelText("Número"), "V-03");
    await u.type(screen.getByLabelText("Partida 1"), "tuberia");
    await u.click(await screen.findByRole("option", { name: /Tuberia de drenaje/ }));
    await u.type(screen.getByLabelText("Cantidad 1"), "50");
    await u.type(screen.getByLabelText("Fuente (acta, oficio)"), "acta 3");
    await u.click(screen.getByRole("button", { name: "Registrar y controlar" }));
    await screen.findByText(/Valuación registrada/);
    expect(envio("/v1/control/valuaciones")?.lineas).toEqual([
      { partida: "OB-B", cantidad: "50", fecha_medicion: "", observacion: "", causa: null },
    ]);
  });

  test("una partida que no está en el contrato no se ofrece «tal cual» y no se envía", async () => {
    const u = await montarEnValuaciones();
    await u.type(screen.getByLabelText("Partida 1"), "OB-D");
    expect(await screen.findByText(/No encontramos «OB-D»/)).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /tal cual/ })).toBeNull();
    await u.type(screen.getByLabelText("Cantidad 1"), "5");
    await u.type(screen.getByLabelText("Fuente (acta, oficio)"), "acta 3");
    await u.click(screen.getByRole("button", { name: "Registrar y controlar" }));
    expect(await screen.findByText(/«OB-D» no está en el contrato/)).toBeInTheDocument();
    expect(screen.getByLabelText("Partida 1")).toHaveAttribute("aria-invalid", "true");
    expect(envio("/v1/control/valuaciones")).toBeUndefined();
  });

  test("un código escrito completo, aunque no se haya elegido de la lista, vale si es del contrato", async () => {
    const u = await montarEnValuaciones();
    await u.type(screen.getByLabelText("Partida 1"), "ob-c");
    await u.type(screen.getByLabelText("Cantidad 1"), "7");
    await u.type(screen.getByLabelText("Fuente (acta, oficio)"), "acta 3");
    await u.click(screen.getByRole("button", { name: "Registrar y controlar" }));
    await screen.findByText(/Valuación registrada/);
    expect(envio("/v1/control/valuaciones")?.lineas).toEqual([
      { partida: "OB-C", cantidad: "7", fecha_medicion: "", observacion: "", causa: null },
    ]);
  });

  test("si las partidas no se pueden leer, el campo sigue siendo de texto libre y lo dice", async () => {
    partidas = () => json({ detalle: "No se pudo leer." }, 503);
    const u = await montarEnValuaciones();
    expect(await screen.findByText(/No se pudieron cargar las partidas del contrato/)).toBeInTheDocument();
    await u.type(screen.getByLabelText("Partida 1"), "OB-Z");
    await u.type(screen.getByLabelText("Cantidad 1"), "5");
    await u.type(screen.getByLabelText("Fuente (acta, oficio)"), "acta 3");
    await u.click(screen.getByRole("button", { name: "Registrar y controlar" }));
    await screen.findByText(/Valuación registrada/);
    expect((envio("/v1/control/valuaciones")?.lineas as { partida: string }[])[0]?.partida).toBe("OB-Z");
  });

  // R13 juzga una valuacion contra la linea base vigente a su corte (su «hasta»): la lista que guia «Partida» se pide
  // para esa fecha. Oraculo a mano: desde el 20/11 rige una linea base sobre OB-002, que solo presupuesta A y B.
  test("con el «Período hasta» escrito, las partidas son las de la línea base vigente a ese corte y se juzga con ellas", async () => {
    partidas = () => json(PARTIDAS);
    const original = fetchFalso.getMockImplementation()!;
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://x");
      if (url.pathname === "/v1/control/partidas" && url.searchParams.get("corte") === "2026-11-20") {
        return json({ version: "OB-002", aviso: "", truncada: false, partidas: PARTIDAS.partidas.slice(0, 2) });
      }
      return original(entrada, init);
    });
    const u = await montarEnValuaciones();
    await u.type(screen.getByLabelText("Período hasta"), "2026-11-20");
    await waitFor(() =>
      expect(fetchFalso.mock.calls.map(([u]) => String(u))).toContain("/v1/control/partidas?proyecto=OB-S2&corte=2026-11-20"),
    );
    await u.type(screen.getByLabelText("Partida 1"), "OB-C");
    await u.type(screen.getByLabelText("Cantidad 1"), "5");
    await u.type(screen.getByLabelText("Fuente (acta, oficio)"), "acta 3");
    await u.click(screen.getByRole("button", { name: "Registrar y controlar" }));
    expect(await screen.findByText("La partida «OB-C» no está en el contrato (versión OB-002): elíjala de la lista.")).toBeInTheDocument();
    expect(envio("/v1/control/valuaciones")).toBeUndefined();
  });

  // Ronda 2 del dictamen (MENOR 4): el aviso que manda GET /v1/control/partidas cuando no hay lista («No hay una línea base
  // vigente a esa fecha de corte.») se perdia y el campo solo decia que la lista no estaba disponible.
  test("con un «Período hasta» sin línea base vigente, la pantalla dice el aviso de la API tal cual", async () => {
    const AVISO_AL_CORTE = "No hay una línea base vigente a esa fecha de corte.";
    const original = fetchFalso.getMockImplementation()!;
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://x");
      if (url.pathname === "/v1/control/partidas" && url.searchParams.get("corte") === "2026-01-05") {
        return json({ version: "", aviso: AVISO_AL_CORTE, truncada: false, partidas: [] });
      }
      return original(entrada, init);
    });
    const u = await montarEnValuaciones();
    expect(screen.queryByText(AVISO_AL_CORTE)).toBeNull();
    await u.type(screen.getByLabelText("Período hasta"), "2026-01-05");
    expect(await screen.findByText(AVISO_AL_CORTE)).toBeInTheDocument();
  });

  test("sin línea base, el aviso de la API se dice y no se confunde con un fallo de lectura", async () => {
    const AVISO = "Este proyecto todavía no tiene línea base.";
    partidas = () => json({ version: "", aviso: AVISO, truncada: false, partidas: [] });
    await montarEnValuaciones();
    expect((await screen.findAllByText(AVISO)).length).toBeGreaterThan(0);
    expect(screen.queryByText(/No se pudieron cargar las partidas del contrato/)).toBeNull();
  });

  test("con la lista recortada, una partida que no se ve no se rechaza: decide el servidor", async () => {
    partidas = () => json({ ...PARTIDAS, truncada: true });
    const u = await montarEnValuaciones();
    expect(
      await screen.findByText("La lista muestra solo parte de las partidas del contrato: si la suya no aparece, escriba su código."),
    ).toBeInTheDocument();
    await u.type(screen.getByLabelText("Partida 1"), "OB-D");
    await u.type(screen.getByLabelText("Cantidad 1"), "5");
    await u.type(screen.getByLabelText("Fuente (acta, oficio)"), "acta 3");
    await u.click(screen.getByRole("button", { name: "Registrar y controlar" }));
    await screen.findByText(/Valuación registrada/);
    expect((envio("/v1/control/valuaciones")?.lineas as { partida: string }[])[0]?.partida).toBe("OB-D");
    expect(screen.getByLabelText("Partida 1")).not.toHaveAttribute("aria-invalid", "true");
  });

  test("«Partida (opcional)» del costo ofrece las del contrato y también deja un gasto general o una partida ajena", async () => {
    const u = await montarEnValuaciones();
    const campo = screen.getByLabelText("Partida (opcional)");
    expect(campo).toHaveAttribute("role", "combobox");
    await u.type(campo, "relleno");
    await u.click(await screen.findByRole("option", { name: /Relleno compactado/ }));
    expect(campo).toHaveValue("OB-C");
    await u.clear(campo);
    await u.type(campo, "OB-D");
    await u.click(await screen.findByRole("option", { name: /Usar «OB-D» tal cual/ }));
    expect(campo).toHaveValue("OB-D");
    await u.type(screen.getByLabelText("Monto"), "10");
    await u.type(screen.getByLabelText("Fuente del costo"), "factura 1");
    await u.click(screen.getByRole("button", { name: "Anotar costo" }));
    await screen.findByText(/Costo anotado/);
    expect(envio("/v1/control/costos")).toMatchObject({ proyecto: "OB-S2", partida: "OB-D", monto: "10" });
  });

  test("el costo puede quedar sin partida (gasto general)", async () => {
    const u = await montarEnValuaciones();
    await u.type(screen.getByLabelText("Monto"), "10");
    await u.type(screen.getByLabelText("Fuente del costo"), "factura 2");
    await u.click(screen.getByRole("button", { name: "Anotar costo" }));
    await screen.findByText(/Costo anotado/);
    expect(envio("/v1/control/costos")).toMatchObject({ partida: "" });
  });
});
