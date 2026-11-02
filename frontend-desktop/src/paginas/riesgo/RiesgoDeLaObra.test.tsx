import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import RiesgoDeLaObra from "./RiesgoDeLaObra";

// Datos ficticios. La pantalla no calcula ningún percentil ni la reserva: los manda el servidor con punto decimal y aquí
// solo se leen con coma decimal y punto de miles, en centésimas. Lo que se teclea con coma o punto de miles («2.000»)
// viaja a la API como número sin separadores (fila 90 de las preguntas para Eugenio).
const ANA: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "ver_riesgo"],
  modo_entrega: false,
};

const INSUMOS = {
  proyecto: "Vía Demo",
  version: "VIA-002",
  moneda: "USD",
  insumos: ["Cemento asfáltico", "Flete", "Gasoil", "Señalización"],
  componentes: [],
  mezclas: [],
  series: [
    { codigo: "CEMENTO_ASFALTICO_PPI", nombre: "PPI de asfalto (proxy internacional)" },
    { codigo: "GASOIL_USD", nombre: "Gasoil, precio administrado" },
  ],
  inicio_linea_base: "2027-02-01",
};

const PROYECCION = {
  proyecto: "Vía Demo",
  version: "VIA-002",
  moneda: "USD",
  inicio: "2027-02-01",
  inicio_de: "linea_base",
  meses: 6,
  trayectorias: 2000,
  semilla: 1,
  total_base: "1000",
  p50: "1248.7171",
  p80: "1302.4561",
  reserva: "302.4561",
  contribucion: [
    { insumo: "Cemento asfáltico", monto: "200.5" },
    { insumo: "Gasoil", monto: "60.1234" },
    { insumo: "Flete", monto: "30" },
    { insumo: "Señalización", monto: "5" },
  ],
  meses_usados: 24,
  supuestos: ["gasto uniforme en el plazo"],
  mezclas: [],
};

const COMPROBACION = {
  moneda: "USD",
  meses: 6,
  trayectorias_por_corte: 500,
  cortes: [{ corte: "2026-02-01", p50: "1200", p80: "1250", real: "1240", dentro: true }],
  cobertura: "0.8421052631578947368421052632",
  cobertura_pct: "84.21",
  dentro: 16,
  n_cortes: 19,
};

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

// El valor que acompaña a un rótulo de una lista de definiciones (<dt>rótulo</dt><dd>valor</dd>).
function valorDe(region: HTMLElement, rotulo: string): string | null {
  const dt = within(region).getByText(rotulo, { selector: "dt" });
  return dt.nextElementSibling?.textContent ?? null;
}

describe("Riesgo de la obra", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let proyeccion: () => Response | Promise<Response>;
  let comprobacion: () => Response | Promise<Response>;
  let usuario: ReturnType<typeof userEvent.setup>;
  const alExpirar = vi.fn();

  function montar() {
    render(
      <ContextoAplicacion.Provider value={{ sesion: ANA, proyecto: "7", nombreProyecto: "Vía Demo", caso: null, recargarProyectos: vi.fn(), alExpirar }}>
        <MemoryRouter>
          <RiesgoDeLaObra />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  function cuerpoDe(ruta: string): Record<string, unknown> {
    const llamada = fetchFalso.mock.calls.find((c) => new URL(String(c[0]), "http://prueba").pathname === ruta);
    return JSON.parse(String(llamada?.[1]?.body)) as Record<string, unknown>;
  }

  beforeEach(() => {
    usuario = userEvent.setup();
    fijarCsrf("tok");
    alExpirar.mockReset();
    fetchFalso.mockReset();
    vi.stubGlobal("fetch", fetchFalso);
    proyeccion = () => json(PROYECCION);
    comprobacion = () => json(COMPROBACION);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      const metodo = init?.method ?? "GET";
      if (url.pathname === "/v1/hoja/versiones") {
        return json({ proyecto: "Vía Demo", moneda: "USD", por_omision: "VIA-002", versiones: [{ codigo: "VIA-001" }, { codigo: "VIA-002" }] });
      }
      if (url.pathname === "/v1/riesgo/insumos" && metodo === "GET") return json(INSUMOS);
      if (url.pathname === "/v1/riesgo/proyeccion" && metodo === "POST") return proyeccion();
      if (url.pathname === "/v1/riesgo/comprobacion" && metodo === "POST") return comprobacion();
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  test("tiene un solo h1 y ofrece la fecha de la línea base", async () => {
    montar();
    expect(screen.getByRole("heading", { level: 1, name: "Riesgo de la obra" })).toBeInTheDocument();
    expect(await screen.findByText(/Si la deja vacía se toma la de la línea base: 01\/02\/2027/)).toBeInTheDocument();
  });

  test("muestra P50, P80, reserva y los tres insumos que más empujan, con coma decimal", async () => {
    montar();
    await usuario.selectOptions(await screen.findByLabelText("Cemento asfáltico"), "CEMENTO_ASFALTICO_PPI");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    const region = await screen.findByRole("region", { name: "Resultado de la proyección" });
    expect(valorDe(region, "P50")).toBe("1.248,72 USD");
    expect(valorDe(region, "P80")).toBe("1.302,46 USD");
    expect(valorDe(region, "Reserva para cubrir el P80")).toBe("302,46 USD");
    expect(valorDe(region, "Total base")).toBe("1.000,00 USD");
    const tabla = within(region).getByRole("table", { name: "Los tres insumos que más empujan" });
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(filas.map((f) => within(f).getAllByRole("cell").map((c) => c.textContent))).toEqual([
      ["Cemento asfáltico", "200,50 USD"],
      ["Gasoil", "60,12 USD"],
      ["Flete", "30,00 USD"],
    ]);
    expect(within(tabla).queryByText("Señalización")).toBeNull();
    // lo tecleado viaja sin separadores: «2.000» trayectorias son 2000; la fecha vacía, null (la de la línea base)
    const cuerpo = cuerpoDe("/v1/riesgo/proyeccion");
    expect(cuerpo).toMatchObject({ proyecto: "Vía Demo", version: "VIA-002", inicio: null, meses: 6, trayectorias: 2000, semilla: 1, ventana_meses: 36 });
    expect(cuerpo.mapa).toEqual({ "Cemento asfáltico": "CEMENTO_ASFALTICO_PPI" });
  });

  // Tarea 22: el informe de riesgo de la Tarea 21 (`GET /v1/riesgo/reportes/riesgo`) se baja con lo mismo que se proyectó:
  // el servidor vuelve a calcular con la misma semilla y el libro dice de dónde sale cada cifra.
  test("después de proyectar baja el informe de riesgo con lo mismo que se proyectó", async () => {
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    Object.defineProperty(URL, "createObjectURL", { value: () => "blob:falso", configurable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: () => undefined, configurable: true });
    const libros: URL[] = [];
    const leer = fetchFalso.getMockImplementation();
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      if (url.pathname === "/v1/riesgo/reportes/riesgo") {
        libros.push(url);
        return new Response("PK", { status: 200, headers: { "Content-Disposition": 'attachment; filename="riesgo.xlsx"' } });
      }
      return leer!(entrada, init);
    });
    montar();
    await usuario.selectOptions(await screen.findByLabelText("Cemento asfáltico"), "CEMENTO_ASFALTICO_PPI");
    expect(screen.queryByRole("button", { name: "Descargar el informe de riesgo" })).toBeNull();
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    const region = await screen.findByRole("region", { name: "Resultado de la proyección" });
    await usuario.click(within(region).getByRole("button", { name: "Descargar el informe de riesgo" }));
    await waitFor(() => expect(libros).toHaveLength(1));
    const consulta = Object.fromEntries(libros[0].searchParams);
    expect(consulta).toEqual({
      proyecto: "Vía Demo",
      version: "VIA-002",
      meses: "6",
      trayectorias: "2000",
      semilla: "1",
      ventana_meses: "36",
      mapa: JSON.stringify({ "Cemento asfáltico": "CEMENTO_ASFALTICO_PPI" }),
    });
    vi.restoreAllMocks();
  });

  test("una cifra mal escrita no se envía y se dice junto al campo", async () => {
    montar();
    const trayectorias = await screen.findByLabelText("Trayectorias");
    await usuario.clear(trayectorias);
    await usuario.type(trayectorias, "2.5");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    expect(await screen.findByText(/Use la coma para los decimales/)).toBeInTheDocument();
    expect(fetchFalso.mock.calls.some((c) => String(c[0]).includes("/v1/riesgo/proyeccion"))).toBe(false);
  });

  test("muestra la cobertura y el número de cortes", async () => {
    let soltar: (r: Response) => void = () => undefined;
    comprobacion = () => new Promise<Response>((resolver) => (soltar = resolver));
    montar();
    await screen.findByLabelText("Cemento asfáltico");
    await usuario.click(screen.getByRole("button", { name: "Comprobar hacia atrás" }));
    // mientras tanto, el aviso de espera: con 500 trayectorias por corte tarda alrededor de medio minuto
    expect(await screen.findByText(/puede tardar/)).toBeInTheDocument();
    soltar(json(COMPROBACION));
    const region = await screen.findByRole("region", { name: "Comprobación hacia atrás" });
    expect(valorDe(region, "Cobertura")).toBe("84,21 %");
    expect(valorDe(region, "Cortes dentro del P80")).toBe("16 de 19");
    expect(valorDe(region, "Número de cortes")).toBe("19");
    expect(cuerpoDe("/v1/riesgo/comprobacion")).toMatchObject({ trayectorias_por_corte: 500, meses: 6 });
    await waitFor(() => expect(screen.queryByText(/puede tardar/)).toBeNull());
  });

  // Hallazgo 9 del recorrido: sin línea base de control la fecha de inicio es necesaria; el aviso salía bajo el botón, lejos
  // del campo, y el campo no se marcaba.
  const SIN_INICIO = "Indique la fecha de inicio de la obra: la versión no tiene línea base de control de la que tomarla.";

  test("sin línea base la fecha de inicio se marca obligatoria y, vacía, el error va al campo sin llamar al servidor", async () => {
    const leer = fetchFalso.getMockImplementation();
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      if (url.pathname === "/v1/riesgo/insumos") return json({ ...INSUMOS, inicio_linea_base: null });
      return leer!(entrada, init);
    });
    montar();
    const campo = await screen.findByLabelText("Fecha de inicio (obligatoria)");
    expect(campo).toBeRequired();
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    expect(fetchFalso.mock.calls.some((c) => String(c[0]).includes("/v1/riesgo/proyeccion"))).toBe(false);
    expect(campo).toHaveAttribute("aria-invalid", "true");
    expect(campo).toHaveAccessibleDescription(expect.stringContaining(SIN_INICIO));
    expect(campo).toHaveFocus();
    expect(screen.queryByRole("alert", { name: /No se pudo calcular el riesgo/ })).toBeNull();
    // Con la fecha escrita, el error se va y la proyección sale con ella.
    await usuario.type(campo, "2027-03-01");
    expect(campo).not.toHaveAttribute("aria-invalid", "true");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    await screen.findByRole("region", { name: "Resultado de la proyección" });
    expect(cuerpoDe("/v1/riesgo/proyeccion")).toMatchObject({ inicio: "2027-03-01" });
  });

  test("con línea base la fecha de inicio no es obligatoria", async () => {
    montar();
    const campo = await screen.findByLabelText("Fecha de inicio");
    expect(campo).not.toBeRequired();
  });

  test("si el servidor pide la fecha de inicio (422), el error se muestra en el campo y lleva el foco a él", async () => {
    proyeccion = () => json({ detalle: SIN_INICIO }, 422);
    montar();
    await screen.findByLabelText("Cemento asfáltico");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    const campo = screen.getByLabelText(/^Fecha de inicio/);
    await waitFor(() => expect(campo).toHaveAttribute("aria-invalid", "true"));
    expect(campo).toHaveAccessibleDescription(expect.stringContaining(SIN_INICIO));
    await waitFor(() => expect(campo).toHaveFocus());
    expect(screen.queryByText("No se pudo calcular el riesgo")).toBeNull();
  });

  test("el error de pocos meses muestra el número", async () => {
    proyeccion = () => json({ detalle: "solo hay 9 meses completos; se necesitan 12" }, 422);
    montar();
    await screen.findByLabelText("Cemento asfáltico");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    const aviso = await screen.findByRole("alert");
    expect(aviso).toHaveTextContent("solo hay 9 meses completos; se necesitan 12");
    expect(screen.queryByRole("region", { name: "Resultado de la proyección" })).toBeNull();
  });
});
