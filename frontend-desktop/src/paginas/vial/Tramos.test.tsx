import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import Tramos from "./Tramos";

// Datos ficticios. La pantalla no calcula cantidades: las manda el servidor (m2, t y t·km de cada capa) y aquí solo se
// leen con coma decimal y punto de miles. Oráculos a mano (Tarea 7): un tramo de 0 a 1 km de 7,3 m, carpeta de 0,05 m a
// 2,35 t/m3 y planta a 12 km, da 7.300 m2, 857,75 t y 10.293 t·km.
const ANA: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja"],
  modo_entrega: false,
};

const TRAMO = {
  id: "T1",
  progresiva_ini_km: "0",
  progresiva_fin_km: "1",
  ancho_m: "7.3",
  distancia_planta_km: "12",
  capas: [{ tipo: "carpeta", espesor_m: "0.05", densidad_t_m3: "2.35", dosis_l_m2: null }],
  demarcacion: [],
};
const CANTIDADES = [
  { tramo: "T1", codigo: "C-000.000.006", descripcion: "Carpeta asfáltica, tramo T1", unidad: "m2", cantidad: "7300", origen_id: "tramo:T1:capa:1", regla: "longitud*ancho" },
  { tramo: "T1", codigo: "C-000.000.007", descripcion: "Mezcla asfáltica de la carpeta, tramo T1", unidad: "t", cantidad: "857.75", origen_id: "tramo:T1:capa:1", regla: "longitud*ancho*espesor*densidad" },
  { tramo: "T1", codigo: "C-000.000.014", descripcion: "Transporte de mezcla, tramo T1", unidad: "t·km", cantidad: "10293", origen_id: "tramo:T1:capa:1", regla: "longitud*ancho*espesor*densidad*distancia" },
];
const VACIA = { proyecto: "Vía Demo", version: "VIA-001", editable: true, bloqueo: null, heredados_de: null, guardado: null, tramos: [], cantidades: [] };
const CON_TRAMOS = {
  ...VACIA,
  guardado: { usuario: "Ana <ana>", fecha_hora: "2026-10-20T10:30:00", fuente: "Importado de via.csv" },
  tramos: [TRAMO],
  cantidades: CANTIDADES,
};

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

describe("Tramos de la vía", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let tramos: () => Response;
  let importar: () => Response;
  let llevar: () => Response;
  let usuario: ReturnType<typeof userEvent.setup>;
  const alExpirar = vi.fn();

  function montar(nombreProyecto: string | null = "Vía Demo") {
    render(
      <ContextoAplicacion.Provider value={{ sesion: ANA, proyecto: "7", nombreProyecto, caso: null, recargarProyectos: vi.fn(), alExpirar }}>
        <MemoryRouter>
          <Tramos />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  const campoDeArchivo = () => document.querySelector('input[type="file"]') as HTMLInputElement;

  beforeEach(() => {
    usuario = userEvent.setup({ applyAccept: false });
    fijarCsrf("tok");
    alExpirar.mockReset();
    fetchFalso.mockReset();
    vi.stubGlobal("fetch", fetchFalso);
    tramos = () => json(CON_TRAMOS);
    importar = () => json(CON_TRAMOS);
    llevar = () => json({ borrador_id: "b".repeat(22), renglones: 18, version: "VIA-002" });
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      const metodo = init?.method ?? "GET";
      if (url.pathname === "/v1/hoja/versiones") {
        return json({ proyecto: "Vía Demo", moneda: "Bs", por_omision: "VIA-002", versiones: [{ codigo: "VIA-001" }, { codigo: "VIA-002" }] });
      }
      if (url.pathname === "/v1/vial/tramos" && metodo === "GET") return tramos();
      if (url.pathname === "/v1/vial/tramos/importar" && metodo === "POST") return importar();
      if (url.pathname === "/v1/vial/tramos/llevar" && metodo === "POST") return llevar();
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  test("tiene un solo h1 y abre la versión que propone la Hoja", async () => {
    montar();
    expect(screen.getByRole("heading", { level: 1, name: "Tramos de la vía" })).toBeInTheDocument();
    const lista = await screen.findByLabelText("Versión");
    await waitFor(() => expect(lista).toHaveValue("VIA-002"));
    await waitFor(() => {
      const pedido = fetchFalso.mock.calls.map((c) => new URL(String(c[0]), "http://prueba")).find((u) => u.pathname === "/v1/vial/tramos");
      expect(pedido?.searchParams.get("proyecto")).toBe("Vía Demo");
      expect(pedido?.searchParams.get("version")).toBe("VIA-002");
    });
  });

  test("muestra m², t y t·km por tramo con coma decimal y punto de miles", async () => {
    montar();
    const tabla = await screen.findByRole("table", { name: "Cantidades del tramo T1" });
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(filas.map((f) => within(f).getAllByRole("cell").map((c) => c.textContent))).toEqual([
      ["Carpeta asfáltica, tramo T1", "m²", "7.300"],
      ["Mezcla asfáltica de la carpeta, tramo T1", "t", "857,75"],
      ["Transporte de mezcla, tramo T1", "t·km", "10.293"],
    ]);
    expect(screen.getByText("De 0 a 1 km · ancho 7,3 m · planta a 12 km")).toBeInTheDocument();
    expect(screen.getByText(/Guardado por Ana <ana> el 20\/10\/2026 10:30/)).toBeInTheDocument();
  });

  test("una versión que hereda sus tramos lo dice", async () => {
    tramos = () => json({ ...CON_TRAMOS, heredados_de: "VIA-001" });
    montar();
    expect(await screen.findByText("Tramos heredados de la versión VIA-001")).toBeInTheDocument();
  });

  test("una versión con tramos propios no dice nada de herencia", async () => {
    montar();
    await screen.findByRole("table", { name: "Cantidades del tramo T1" });
    expect(screen.queryByText(/heredados/)).toBeNull();
  });

  test("una versión sin tramos invita a importarlos", async () => {
    tramos = () => json(VACIA);
    montar();
    expect(await screen.findByText("Esta versión aún no tiene tramos. Importe el archivo de la vía.")).toBeInTheDocument();
  });

  test("importar manda el archivo como multipart y avisa con el foco en el aviso", async () => {
    importar = () => json({ ...CON_TRAMOS, guardado: { ...CON_TRAMOS.guardado, fuente: "Importado de via.csv" } });
    montar();
    await screen.findByRole("table", { name: "Cantidades del tramo T1" });
    await usuario.upload(campoDeArchivo(), new File(["tramo;x"], "via.csv", { type: "text/csv" }));
    const aviso = await screen.findByText("Tramos importados: 1 tramo de via.csv.");
    await waitFor(() => expect(document.activeElement).toBe(aviso.closest("[tabindex]")));
    const llamada = fetchFalso.mock.calls.find((c) => String(c[0]).startsWith("/v1/vial/tramos/importar"));
    expect(String(llamada?.[0])).toContain("proyecto=V%C3%ADa%20Demo");
    expect(llamada?.[1]?.method).toBe("POST");
    expect(llamada?.[1]?.body).toBeInstanceOf(FormData);
  });

  test("el error de importación nombra la fila, recibe el foco y no cambia lo mostrado", async () => {
    importar = () => json({ detalle: "el archivo 'via.csv', fila 7: la progresiva final (1.2) debe ser mayor que la inicial (2.0)" }, 422);
    montar();
    await screen.findByRole("table", { name: "Cantidades del tramo T1" });
    await usuario.upload(campoDeArchivo(), new File(["x"], "via.csv", { type: "text/csv" }));
    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("fila 7");
    expect(alerta).toHaveTextContent("No se importó ningún tramo");
    await waitFor(() => expect(alerta.closest("[tabindex]")).toBe(document.activeElement));
    expect(screen.getByRole("table", { name: "Cantidades del tramo T1" })).toBeInTheDocument();
  });

  test("una versión aprobada dice por qué no se importa y no ofrece la zona de soltar", async () => {
    tramos = () => json({ ...CON_TRAMOS, editable: false, bloqueo: "La versión VIA-002 está aprobada: sus tramos ya no se editan. Guarde una versión nueva y cargue los tramos allí." });
    montar();
    expect(await screen.findByText(/La versión VIA-002 está aprobada/)).toBeInTheDocument();
    expect(campoDeArchivo()).toBeNull();
    expect(screen.getByRole("table", { name: "Cantidades del tramo T1" })).toBeInTheDocument();
  });

  test("llevar muestra cuántos renglones, de qué versión, y enlaza al Presupuesto", async () => {
    montar();
    await screen.findByRole("table", { name: "Cantidades del tramo T1" });
    await usuario.click(screen.getByRole("button", { name: "Llevar al presupuesto" }));
    const aviso = await screen.findByText("Se llevaron 18 renglones de VIA-002 al Presupuesto de la obra.");
    await waitFor(() => expect(document.activeElement).toBe(aviso.closest("[tabindex]")));
    expect(screen.getByRole("link", { name: "Abrir el presupuesto" })).toHaveAttribute("href", "/hoja");
    const llamada = fetchFalso.mock.calls.find((c) => String(c[0]) === "/v1/vial/tramos/llevar");
    expect(llamada?.[1]?.method).toBe("POST");
    expect(JSON.parse(String(llamada?.[1]?.body))).toEqual({ proyecto: "Vía Demo", version: "VIA-002" });
  });

  test("lleva la versión elegida en el selector", async () => {
    llevar = () => json({ borrador_id: "b".repeat(22), renglones: 18, version: "VIA-001" });
    montar();
    await screen.findByRole("table", { name: "Cantidades del tramo T1" });
    await usuario.selectOptions(screen.getByLabelText("Versión"), "VIA-001");
    await screen.findByRole("table", { name: "Cantidades del tramo T1" });
    await usuario.click(screen.getByRole("button", { name: "Llevar al presupuesto" }));
    expect(await screen.findByText("Se llevaron 18 renglones de VIA-001 al Presupuesto de la obra.")).toBeInTheDocument();
    const llamada = fetchFalso.mock.calls.find((c) => String(c[0]) === "/v1/vial/tramos/llevar");
    expect(JSON.parse(String(llamada?.[1]?.body))).toEqual({ proyecto: "Vía Demo", version: "VIA-001" });
  });

  test("el 409 de un borrador de otra versión se muestra tal cual, con foco", async () => {
    const detalle =
      "El Presupuesto de la obra tiene abierto un borrador de VIA-001; está viendo los tramos de VIA-002. Guarde o descarte ese borrador en el Presupuesto, o elija VIA-001 aquí, y vuelva a llevar.";
    llevar = () => json({ detalle }, 409);
    montar();
    await screen.findByRole("table", { name: "Cantidades del tramo T1" });
    await usuario.click(screen.getByRole("button", { name: "Llevar al presupuesto" }));
    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(detalle);
    await waitFor(() => expect(alerta.closest("[tabindex]")).toBe(document.activeElement));
    expect(screen.queryByRole("link", { name: "Abrir el presupuesto" })).toBeNull();
  });

  test("llevar un solo renglón lo dice en singular", async () => {
    llevar = () => json({ borrador_id: "b".repeat(22), renglones: 1, version: "VIA-002" });
    montar();
    await screen.findByRole("table", { name: "Cantidades del tramo T1" });
    await usuario.click(screen.getByRole("button", { name: "Llevar al presupuesto" }));
    expect(await screen.findByText("Se llevó 1 renglón de VIA-002 al Presupuesto de la obra.")).toBeInTheDocument();
  });

  test("el 404 nombra las partidas sin APU", async () => {
    const detalle = "Las partidas «C-000.000.012» y «C-000.000.013» no están en el catálogo: compóngalas primero en Componer.";
    llevar = () => json({ detalle }, 404);
    montar();
    await screen.findByRole("table", { name: "Cantidades del tramo T1" });
    await usuario.click(screen.getByRole("button", { name: "Llevar al presupuesto" }));
    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent(detalle);
    expect(alerta).toHaveTextContent("No se llevó nada al presupuesto");
    await waitFor(() => expect(alerta.closest("[tabindex]")).toBe(document.activeElement));
    expect(screen.queryByRole("link", { name: "Abrir el presupuesto" })).toBeNull();
  });

  test("sin tramos no ofrece llevarlos", async () => {
    tramos = () => json(VACIA);
    montar();
    await screen.findByText("Esta versión aún no tiene tramos. Importe el archivo de la vía.");
    expect(screen.queryByRole("button", { name: "Llevar al presupuesto" })).toBeNull();
  });

  // Tarea 22: los reportes de la Tarea 21 se descargan desde la pantalla (`GET /v1/vial/reportes/{tipo}`) con la obra y
  // la versión que se ven; el servidor arma el libro y propone el nombre.
  test("ofrece los tres reportes de la vía y baja cada uno con la obra y la versión que se ven", async () => {
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    Object.defineProperty(URL, "createObjectURL", { value: () => "blob:falso", configurable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: () => undefined, configurable: true });
    const libros: URL[] = [];
    const leer = fetchFalso.getMockImplementation();
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      if (url.pathname.startsWith("/v1/vial/reportes/")) {
        libros.push(url);
        return new Response("PK", { status: 200, headers: { "Content-Disposition": 'attachment; filename="libro.xlsx"' } });
      }
      return leer!(entrada, init);
    });
    montar();
    const grupo = await screen.findByRole("region", { name: "Reportes de la vía" });
    for (const etiqueta of ["Cómputos por tramo", "APU con origen y conciliación", "Resumen con IVA"]) {
      await usuario.click(within(grupo).getByRole("button", { name: etiqueta }));
    }
    await waitFor(() => expect(libros).toHaveLength(3));
    expect(libros.map((u) => [u.pathname, u.searchParams.get("proyecto"), u.searchParams.get("version")])).toEqual([
      ["/v1/vial/reportes/computos", "Vía Demo", "VIA-002"],
      ["/v1/vial/reportes/apu", "Vía Demo", "VIA-002"],
      ["/v1/vial/reportes/resumen", "Vía Demo", "VIA-002"],
    ]);
    vi.restoreAllMocks();
  });

  test("sin tramos no ofrece los reportes de la vía", async () => {
    tramos = () => json(VACIA);
    montar();
    await screen.findByText("Esta versión aún no tiene tramos. Importe el archivo de la vía.");
    expect(screen.queryByRole("region", { name: "Reportes de la vía" })).toBeNull();
  });

  test("sin obra abierta lo dice y no pide nada", async () => {
    montar(null);
    expect(screen.getByText("Abra una obra para ver o importar sus tramos.")).toBeInTheDocument();
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  test("un 401 al leer avisa a la aplicación", async () => {
    tramos = () => json({ detalle: "Sesión vencida" }, 401);
    montar();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });
});
