import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import type { ObraAbierta } from "../../marco/obraAbierta";
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
  let guardarMapa: () => Response | Promise<Response>;
  let usuario: ReturnType<typeof userEvent.setup>;
  const alExpirar = vi.fn();

  function montar(sesion: SesionRespuesta = ANA, obra?: ObraAbierta) {
    const contenido = obra ? (
      <ContextoDeLaObra.Provider value={obra}>
        <RiesgoDeLaObra />
      </ContextoDeLaObra.Provider>
    ) : (
      <RiesgoDeLaObra />
    );
    render(
      <ContextoAplicacion.Provider value={{ sesion, proyecto: "7", nombreProyecto: "Vía Demo", caso: null, recargarProyectos: vi.fn(), alExpirar }}>
        <MemoryRouter>{contenido}</MemoryRouter>
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
    guardarMapa = () => json({ guardado: true });
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      const metodo = init?.method ?? "GET";
      if (url.pathname === "/v1/hoja/versiones") {
        return json({ proyecto: "Vía Demo", moneda: "USD", por_omision: "VIA-002", versiones: [{ codigo: "VIA-001" }, { codigo: "VIA-002" }] });
      }
      if (url.pathname === "/v1/riesgo/insumos" && metodo === "GET") return json(INSUMOS);
      if (url.pathname === "/v1/riesgo/proyeccion" && metodo === "POST") return proyeccion();
      if (url.pathname === "/v1/riesgo/comprobacion" && metodo === "POST") return comprobacion();
      if (url.pathname === "/v1/riesgo/mapa" && metodo === "PUT") return guardarMapa();
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
    expect(valorDe(region, "Costo probable (P50, mitad de los escenarios)")).toBe("1.248,72 USD");
    expect(valorDe(region, "Costo conservador (P80, cubre 8 de cada 10 escenarios)")).toBe("1.302,46 USD");
    expect(valorDe(region, "Reserva recomendada para cubrir el P80")).toBe("302,46 USD");
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

  // Prueba en vivo del 2026-11-18: en la demo (obra en USD) se proyectó sin elegir series y todo salió igual al total
  // base, sin decir por qué. En USD un insumo sin serie queda fijo: el resultado lo dice y lleva a elegir la serie.
  test("si nada se movió en una obra en USD sin series elegidas, dice que solo se mueven los insumos con serie", async () => {
    const plana = { ...PROYECCION, moneda: "USD", p50: "1000", p80: "1000", reserva: "0", contribucion: [] };
    proyeccion = () => json(plana);
    montar();
    await screen.findByLabelText("Cemento asfáltico");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    const region = await screen.findByRole("region", { name: "Resultado de la proyección" });
    expect(cuerpoDe("/v1/riesgo/proyeccion").mapa).toEqual({});
    expect(
      within(region).getByText(
        "Ningún insumo se movió con la historia usada. En una obra en USD solo se mueven los insumos que siguen una serie: elíjala en «Serie que mueve cada insumo».",
      ),
    ).toBeInTheDocument();
  });

  // Con series elegidas no se pide elegirlas otra vez: no variaron en la ventana (si hubieran bajado, la contribución
  // traería montos negativos y se verían en la tabla).
  test("si nada se movió en una obra en USD con series elegidas, dice que esas series no variaron", async () => {
    const plana = { ...PROYECCION, moneda: "USD", p50: "1000", p80: "1000", reserva: "0", contribucion: [] };
    proyeccion = () => json(plana);
    montar();
    await usuario.selectOptions(await screen.findByLabelText("Gasoil"), "GASOIL_USD");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    const region = await screen.findByRole("region", { name: "Resultado de la proyección" });
    expect(
      within(region).getByText(
        "Ningún insumo se movió con la historia usada: las series elegidas no variaron en los meses de historia usados.",
      ),
    ).toBeInTheDocument();
    expect(within(region).queryByText(/elíjala en «Serie que mueve cada insumo»/)).toBeNull();
  });

  test("si nada se movió en una obra en Bs, no pide elegir una serie (sin serie sigue a la tasa)", async () => {
    const plana = { ...PROYECCION, moneda: "Bs", p50: "1000", p80: "1000", reserva: "0", contribucion: [] };
    proyeccion = () => json(plana);
    montar();
    await screen.findByLabelText("Cemento asfáltico");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    const region = await screen.findByRole("region", { name: "Resultado de la proyección" });
    expect(within(region).getByText("Ningún insumo se movió con la historia usada.")).toBeInTheDocument();
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

  test("«Simulaciones por fecha probada» está en la sección «Probar precisión con meses pasados» y no en la de «Proyectar»", async () => {
    montar();
    const porCorte = await screen.findByLabelText("Simulaciones por fecha probada");
    const comprobar = screen.getByRole("group", { name: "Probar precisión con meses pasados" });
    const proyectar = screen.getByRole("group", { name: "Proyectar" });
    expect(comprobar).toContainElement(porCorte);
    expect(proyectar).not.toContainElement(porCorte);
    expect(within(comprobar).getByRole("button", { name: "Probar precisión con meses pasados" })).toBeInTheDocument();
    expect(within(proyectar).getByRole("button", { name: "Proyectar" })).toBeInTheDocument();
  });

  test("«Fecha de inicio» y «Simulaciones a correr» están en «Proyectar», y los parámetros comunes fuera de ambos grupos", async () => {
    montar();
    const inicio = await screen.findByLabelText("Fecha de inicio");
    const trayectorias = screen.getByLabelText("Simulaciones a correr");
    const porCorte = screen.getByLabelText("Simulaciones por fecha probada");
    const meses = screen.getByLabelText("Meses del plazo");
    const semilla = screen.getByLabelText("Número de repetición (semilla)");
    const historia = screen.getByLabelText("Meses de historia");
    const proyectar = screen.getByRole("group", { name: "Proyectar" });
    const comprobar = screen.getByRole("group", { name: "Probar precisión con meses pasados" });

    expect(screen.getByText("2.000 ofrece resultados estables")).toBeInTheDocument();
    expect(screen.getByText("Déjelo en 1; con el mismo número repite exactamente el resultado")).toBeInTheDocument();
    expect(proyectar).toContainElement(inicio);
    expect(proyectar).toContainElement(trayectorias);
    expect(comprobar).not.toContainElement(inicio);
    expect(comprobar).not.toContainElement(trayectorias);

    expect(comprobar).toContainElement(porCorte);
    expect(proyectar).not.toContainElement(porCorte);

    expect(proyectar).not.toContainElement(meses);
    expect(proyectar).not.toContainElement(semilla);
    expect(proyectar).not.toContainElement(historia);
    expect(comprobar).not.toContainElement(meses);
    expect(comprobar).not.toContainElement(semilla);
    expect(comprobar).not.toContainElement(historia);
  });

  test("una cifra mal escrita no se envía y se dice junto al campo", async () => {
    montar();
    const trayectorias = await screen.findByLabelText("Simulaciones a correr");
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
    await usuario.click(screen.getByRole("button", { name: "Probar precisión con meses pasados" }));
    // mientras tanto, el aviso de espera: con 500 trayectorias por corte tarda alrededor de medio minuto
    expect(await screen.findByText(/puede tardar/)).toBeInTheDocument();
    soltar(json(COMPROBACION));
    const region = await screen.findByRole("region", { name: "Comprobación hacia atrás" });
    expect(valorDe(region, "Aciertos de la prueba (cobertura)")).toBe("84,21 %");
    expect(valorDe(region, "Fechas pasadas cubiertas por el P80")).toBe("16 de 19");
    expect(valorDe(region, "Fechas pasadas probadas")).toBe("19");
    expect(
      within(region).getByText(
        /Cerca de 80 % o más indica que la proyección habría cubierto bien las subidas pasadas \(es una referencia histórica, no una garantía\)\./,
      ),
    ).toBeInTheDocument();
    expect(cuerpoDe("/v1/riesgo/comprobacion")).toMatchObject({ trayectorias_por_corte: 500, meses: 6 });
    await waitFor(() => expect(screen.queryByText(/puede tardar/)).toBeNull());
  });

  test("sin versiones guardadas remite al presupuesto con un botón principal", async () => {
    const leer = fetchFalso.getMockImplementation();
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      if (url.pathname === "/v1/hoja/versiones") return json({ proyecto: "Vía Demo", moneda: "USD", por_omision: null, versiones: [] });
      return leer!(entrada, init);
    });
    montar();
    expect(await screen.findByText("Esta obra aún no tiene versiones")).toBeInTheDocument();
    expect(
      screen.getByText("Esta obra aún no tiene versiones guardadas. Guarde una en el presupuesto para proyectar su riesgo."),
    ).toBeInTheDocument();
    const boton = screen.getByRole("link", { name: "Ir al presupuesto" });
    expect(boton).toHaveAttribute("href", "/hoja");
    expect(boton).toHaveClass("cds--btn", "cds--btn--primary");
  });

  test("dentro de una obra abierta sin versiones, «Ir al presupuesto» apunta al presupuesto de esa obra", async () => {
    const leer = fetchFalso.getMockImplementation();
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      if (url.pathname === "/v1/hoja/versiones") return json({ proyecto: "Vía Demo", moneda: "USD", por_omision: null, versiones: [] });
      return leer!(entrada, init);
    });
    montar(ANA, { carpeta: "obra.db", obraId: 7, ficha: { estado: "cargando" }, recargarFicha: vi.fn() });
    const boton = await screen.findByRole("link", { name: "Ir al presupuesto" });
    expect(boton).toHaveAttribute("href", "/obra/obra.db/7/presupuesto");
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

  // Falta una serie (prueba en vivo del 2026-11-18, hallazgo 4; series viales cargables en «Índices del BCV»): el aviso
  // trae el nombre de la serie y dónde se carga, y quien administra los precios tiene el enlace a esa pantalla.
  const FALTA_UNA_SERIE =
    "Solo hay 5 meses completos de historia en los 36 meses anteriores al inicio (01/2027); se necesitan 12. Falta historia de: " +
    "«Gasoil, precio administrado» (5 de 36 meses), que se carga en la página «Índices del BCV», sección «Series del riesgo vial».";
  const ADMIN: SesionRespuesta = { ...ANA, login: "admin", roles: ["administrador"], acciones: ["administrar_precios", "ver_riesgo"] };

  test("si falta una serie, quien administra los precios tiene el enlace a donde se carga", async () => {
    proyeccion = () => json({ detalle: FALTA_UNA_SERIE }, 422);
    montar(ADMIN);
    await screen.findByLabelText("Cemento asfáltico");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("sección «Series del riesgo vial»");
    const enlace = await screen.findByRole("link", { name: "Cargar las series en Índices del BCV" });
    expect(enlace).toHaveAttribute("href", "/precios/indices");
  });

  test("la comprobación hacia atrás también ofrece el enlace cuando falta una serie", async () => {
    comprobacion = () => json({ detalle: FALTA_UNA_SERIE }, 422);
    montar(ADMIN);
    await screen.findByLabelText("Cemento asfáltico");
    await usuario.click(screen.getByRole("button", { name: "Probar precisión con meses pasados" }));
    expect(await screen.findByRole("link", { name: "Cargar las series en Índices del BCV" })).toBeInTheDocument();
  });

  test("sin permiso para administrar precios el aviso queda sin enlace (diría 403)", async () => {
    proyeccion = () => json({ detalle: FALTA_UNA_SERIE }, 422);
    montar();
    await screen.findByLabelText("Cemento asfáltico");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Falta historia de");
    expect(screen.queryByRole("link", { name: "Cargar las series en Índices del BCV" })).toBeNull();
  });

  test("un error que no es de series no trae el enlace", async () => {
    proyeccion = () => json({ detalle: "solo hay 9 meses completos; se necesitan 12" }, 422);
    montar(ADMIN);
    await screen.findByLabelText("Cemento asfáltico");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    await screen.findByRole("alert");
    expect(screen.queryByRole("link", { name: "Cargar las series en Índices del BCV" })).toBeNull();
  });

  // Lo que se ve es de la versión elegida: la proyección y la comprobación de VIA-002 no siguen a la vista al elegir
  // VIA-001, porque se leerían como de la nueva versión.
  test("al elegir otra versión se retiran la proyección y la comprobación de la anterior", async () => {
    montar();
    await screen.findByLabelText("Cemento asfáltico");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    await screen.findByRole("region", { name: "Resultado de la proyección" });
    await usuario.click(screen.getByRole("button", { name: "Probar precisión con meses pasados" }));
    await screen.findByRole("region", { name: "Comprobación hacia atrás" });
    await usuario.selectOptions(screen.getByLabelText("Versión"), "VIA-001");
    expect(screen.queryByRole("region", { name: "Resultado de la proyección" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Comprobación hacia atrás" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Descargar el informe de riesgo" })).toBeNull();
  });

  test("mientras se proyecta no se puede cambiar de versión", async () => {
    let soltar: (r: Response) => void = () => undefined;
    proyeccion = () => new Promise<Response>((resolver) => (soltar = resolver));
    montar();
    await screen.findByLabelText("Cemento asfáltico");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    expect(screen.getByLabelText("Versión")).toBeDisabled();
    soltar(json(PROYECCION));
    await screen.findByRole("region", { name: "Resultado de la proyección" });
    expect(screen.getByLabelText("Versión")).toBeEnabled();
  });

  // Mejora de la DS-81 (DS-90 a DS-93): Sílice recuerda en el caso la serie de cada insumo. Al volver, el selector aparece
  // precargado con lo último que se usó en esa versión (o, sin nada propio, en otra versión de la obra); lo que ya no vale
  // se dice y no se precarga. Se guarda en una llamada aparte, después de una proyección o comprobación que salió bien.
  function conPrecarga(mapa_guardado: unknown) {
    const leer = fetchFalso.getMockImplementation();
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      if (url.pathname === "/v1/riesgo/insumos") return json({ ...INSUMOS, mapa_guardado });
      return leer!(entrada, init);
    });
  }

  function guardados(): Record<string, unknown>[] {
    return fetchFalso.mock.calls
      .filter((c) => new URL(String(c[0]), "http://prueba").pathname === "/v1/riesgo/mapa" && c[1]?.method === "PUT")
      .map((c) => JSON.parse(String(c[1]?.body)) as Record<string, unknown>);
  }

  test("precarga la serie que se usó la última vez en esta versión y la envía al proyectar", async () => {
    conPrecarga({ mapa: { Gasoil: "GASOIL_USD" }, de_version: "VIA-002", descartados: [] });
    montar();
    const gasoil = (await screen.findByLabelText("Gasoil")) as HTMLSelectElement;
    expect(gasoil.value).toBe("GASOIL_USD");
    expect((screen.getByLabelText("Cemento asfáltico") as HTMLSelectElement).value).toBe("");
    expect(screen.getByText("Precargado con las series que usó la última vez en esta versión.")).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    await screen.findByRole("region", { name: "Resultado de la proyección" });
    expect(cuerpoDe("/v1/riesgo/proyeccion").mapa).toEqual({ Gasoil: "GASOIL_USD" });
  });

  test("sin mapa propio precarga el de otra versión de la obra y lo dice", async () => {
    conPrecarga({ mapa: { "Cemento asfáltico": "CEMENTO_ASFALTICO_PPI" }, de_version: "VIA-001", descartados: [] });
    montar();
    const asfalto = (await screen.findByLabelText("Cemento asfáltico")) as HTMLSelectElement;
    expect(asfalto.value).toBe("CEMENTO_ASFALTICO_PPI");
    expect(screen.getByText("Precargado con las series que usó la última vez en la versión VIA-001.")).toBeInTheDocument();
  });

  test("lo guardado que ya no vale no se precarga y se dice", async () => {
    conPrecarga({
      mapa: {},
      de_version: "VIA-002",
      descartados: [
        { insumo: "Flete viejo", serie: "GASOIL_USD", motivo: "insumo" },
        { insumo: "Gasoil", serie: "SERIE_RETIRADA", motivo: "serie" },
      ],
    });
    montar();
    await screen.findByLabelText("Gasoil");
    expect(
      screen.getByText(
        "No se precargó la serie de 2 insumos: «Flete viejo» ya no está en esta versión; «Gasoil»: la serie que tenía ya no se ofrece.",
      ),
    ).toBeInTheDocument();
    expect((screen.getByLabelText("Gasoil") as HTMLSelectElement).value).toBe("");
    // No quedó ninguna serie que precargar: la nota de la precarga no se muestra.
    expect(screen.queryByText(/Precargado con las series/)).toBeNull();
  });

  test("lo elegido a mano manda sobre la precarga y la nota se retira", async () => {
    conPrecarga({ mapa: { Gasoil: "GASOIL_USD" }, de_version: "VIA-002", descartados: [] });
    montar();
    await usuario.selectOptions(await screen.findByLabelText("Cemento asfáltico"), "CEMENTO_ASFALTICO_PPI");
    expect((screen.getByLabelText("Gasoil") as HTMLSelectElement).value).toBe("GASOIL_USD");
    expect(screen.queryByText(/Precargado con las series/)).toBeNull();
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    await screen.findByRole("region", { name: "Resultado de la proyección" });
    expect(cuerpoDe("/v1/riesgo/proyeccion").mapa).toEqual({ Gasoil: "GASOIL_USD", "Cemento asfáltico": "CEMENTO_ASFALTICO_PPI" });
  });

  test("después de proyectar bien guarda el mapa usado, en una llamada aparte", async () => {
    montar();
    await usuario.selectOptions(await screen.findByLabelText("Cemento asfáltico"), "CEMENTO_ASFALTICO_PPI");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    await screen.findByRole("region", { name: "Resultado de la proyección" });
    await waitFor(() => expect(guardados()).toHaveLength(1));
    expect(guardados()[0]).toEqual({ proyecto: "Vía Demo", version: "VIA-002", mapa: { "Cemento asfáltico": "CEMENTO_ASFALTICO_PPI" } });
  });

  test("después de comprobar bien también guarda el mapa usado", async () => {
    montar();
    await usuario.selectOptions(await screen.findByLabelText("Gasoil"), "GASOIL_USD");
    await usuario.click(screen.getByRole("button", { name: "Probar precisión con meses pasados" }));
    await screen.findByRole("region", { name: "Comprobación hacia atrás" });
    await waitFor(() => expect(guardados()).toHaveLength(1));
    expect(guardados()[0]).toEqual({ proyecto: "Vía Demo", version: "VIA-002", mapa: { Gasoil: "GASOIL_USD" } });
  });

  test("si la proyección falla no guarda el mapa", async () => {
    proyeccion = () => json({ detalle: "solo hay 9 meses completos; se necesitan 12" }, 422);
    montar();
    await usuario.selectOptions(await screen.findByLabelText("Gasoil"), "GASOIL_USD");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    await screen.findByRole("alert");
    expect(guardados()).toHaveLength(0);
  });

  test("si no se pudo recordar el mapa, el resultado queda y se avisa sin estorbar", async () => {
    guardarMapa = () => json({ detalle: "No se pudo leer o escribir el caso." }, 503);
    montar();
    await screen.findByLabelText("Gasoil");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    const region = await screen.findByRole("region", { name: "Resultado de la proyección" });
    expect(
      await screen.findByText("No se pudo recordar la serie de cada insumo para la próxima vez; el resultado no cambia."),
    ).toBeInTheDocument();
    expect(region).toBeInTheDocument();
  });

  // Revisión de la rama (Neon, 2026-11-20): una precarga que responde con la versión pedida, para ir y volver entre versiones.
  function conPrecargaPorVersion(mapa_guardado: unknown) {
    const leer = fetchFalso.getMockImplementation();
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      if (url.pathname === "/v1/riesgo/insumos") return json({ ...INSUMOS, version: url.searchParams.get("version"), mapa_guardado });
      return leer!(entrada, init);
    });
  }

  test("un guardado del mapa no sale hasta que termina el anterior: el último elegido queda como el último", async () => {
    let soltar: (r: Response) => void = () => undefined;
    let pedidos = 0;
    guardarMapa = () => (++pedidos === 1 ? new Promise<Response>((resolver) => (soltar = resolver)) : json({ guardado: true }));
    montar();
    await usuario.selectOptions(await screen.findByLabelText("Gasoil"), "GASOIL_USD");
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    await screen.findByRole("region", { name: "Resultado de la proyección" });
    await waitFor(() => expect(guardados()).toHaveLength(1));
    await usuario.selectOptions(screen.getByLabelText("Cemento asfáltico"), "CEMENTO_ASFALTICO_PPI");
    await usuario.click(screen.getByRole("button", { name: "Probar precisión con meses pasados" }));
    await screen.findByRole("region", { name: "Comprobación hacia atrás" });
    expect(guardados()).toHaveLength(1);
    soltar(json({ guardado: true }));
    await waitFor(() => expect(guardados()).toHaveLength(2));
    expect(guardados()[1].mapa).toEqual({ Gasoil: "GASOIL_USD", "Cemento asfáltico": "CEMENTO_ASFALTICO_PPI" });
  });

  test("al volver a una versión vuelve lo recordado, no lo que se tocó sin proyectar", async () => {
    conPrecargaPorVersion({ mapa: { Gasoil: "GASOIL_USD" }, de_version: "VIA-002", descartados: [] });
    montar();
    await usuario.selectOptions(await screen.findByLabelText("Gasoil"), "");
    await usuario.selectOptions(screen.getByLabelText("Versión"), "VIA-001");
    await screen.findByText("Precargado con las series que usó la última vez en la versión VIA-002.");
    await usuario.selectOptions(screen.getByLabelText("Versión"), "VIA-002");
    await waitFor(() => expect((screen.getByLabelText("Gasoil") as HTMLSelectElement).value).toBe("GASOIL_USD"));
    expect(screen.getByText("Precargado con las series que usó la última vez en esta versión.")).toBeInTheDocument();
  });

  test("sin ninguna serie recordada no dice que precargó", async () => {
    conPrecarga({ mapa: {}, de_version: "VIA-002", descartados: [] });
    montar();
    await screen.findByLabelText("Gasoil");
    expect(screen.queryByText(/Precargado con las series/)).toBeNull();
  });

  test("el aviso de lo que no se precargó se retira al elegir a mano", async () => {
    conPrecarga({
      mapa: { Gasoil: "GASOIL_USD" },
      de_version: "VIA-002",
      descartados: [{ insumo: "Flete viejo", serie: "GASOIL_USD", motivo: "insumo" }],
    });
    montar();
    await usuario.selectOptions(await screen.findByLabelText("Cemento asfáltico"), "CEMENTO_ASFALTICO_PPI");
    expect(screen.queryByText(/No se precargó la serie/)).toBeNull();
  });

  test("guardado el mapa propio, se retiran la nota de la otra versión y el aviso de lo descartado", async () => {
    conPrecarga({
      mapa: { "Cemento asfáltico": "CEMENTO_ASFALTICO_PPI" },
      de_version: "VIA-001",
      descartados: [{ insumo: "Flete viejo", serie: "GASOIL_USD", motivo: "insumo" }],
    });
    montar();
    await screen.findByText("Precargado con las series que usó la última vez en la versión VIA-001.");
    expect(screen.getByText(/No se precargó la serie de 1 insumo/)).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Proyectar" }));
    await screen.findByRole("region", { name: "Resultado de la proyección" });
    await waitFor(() => expect(guardados()).toHaveLength(1));
    await waitFor(() => expect(screen.queryByText(/Precargado con las series/)).toBeNull());
    expect(screen.queryByText(/No se precargó la serie/)).toBeNull();
    expect((screen.getByLabelText("Cemento asfáltico") as HTMLSelectElement).value).toBe("CEMENTO_ASFALTICO_PPI");
  });
});
