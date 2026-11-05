// AC2 (pedido de Eugenio, 2026-10-21): en Reajuste, «Serie» de los componentes y «Partida» de lo ejecutado ofrecen lo que
// ya existe: las series importadas (GET /v1/reajuste/series) y las partidas de la versión del contrato elegida
// (GET /v1/reajuste/partidas). El servidor las rechaza si no existen («la partida X no está en la versión del contrato»,
// «las series X no están importadas»), así que no se ofrece usar «tal cual» cuando la lista se pudo leer.
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaReajuste from "./index";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["convertir_y_reajustar"],
  modo_entrega: false,
};

const PROYECTOS = [{ codigo: "1", nombre: "Contrato S1", version_vigente: 2, version_codigo: "002", actualizado: null }];
const CONTEXTO = {
  versiones: [
    { codigo: "001", motivo: "", revalorada: false },
    { codigo: "002", motivo: "revaloracion", revalorada: true },
  ],
  periodicidades: ["mensual", "trimestral"],
  mecanismos: ["escalatoria", "comprobacion", "ambos"],
  estructuras: ["por_partida", "declarada"],
  componentes: ["materiales", "equipos", "mano_obra"],
};
const SERIES = [
  { clave: "FIC-EQU", nombre: "Índice de equipos", organismo: "BCV", unidad: "indice_bs", periodicidad: "mensual" },
  { clave: "FIC-MAT", nombre: "Índice de materiales", organismo: "BCV", unidad: "indice_bs", periodicidad: "mensual" },
];
const PARTIDAS_001 = {
  version: "001",
  aviso: "",
  partidas: [
    { codigo: "S1-R01", descripcion: "Partida ficticia", unidad: "m3" },
    { codigo: "S1-R02", descripcion: "Cuneta de concreto", unidad: "m" },
  ],
};
const PARTIDAS_002 = { version: "002", aviso: "", partidas: [{ codigo: "S1-R09", descripcion: "Solo de la segunda", unidad: "und" }] };

describe("Reajuste: autocompletado de la serie y de la partida (AC2)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let series: () => Response;
  let partidas: (version: string) => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    series = () => json(SERIES);
    partidas = (version) => json(version === "002" ? PARTIDAS_002 : PARTIDAS_001);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://x");
      if (url.pathname === "/v1/proyectos") return json(PROYECTOS);
      if (url.pathname === "/v1/reajuste/contexto") return json(CONTEXTO);
      if (url.pathname === "/v1/reajuste/series") return series();
      if (url.pathname === "/v1/reajuste/partidas") return partidas(url.searchParams.get("version") ?? "");
      if (url.pathname === "/v1/reajuste/calcular" && init?.method === "POST") {
        return json({ estado: "cerrado", moneda: "Bs", columnas: ["Período"], filas: [{ Período: "Total" }], avisos: [], mensaje_parcial: "", parciales: [] });
      }
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  async function montar() {
    const aplicacion: Aplicacion = { sesion: SESION, proyecto: "1", caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() };
    render(
      <ContextoAplicacion.Provider value={aplicacion}>
        <PaginaReajuste />
      </ContextoAplicacion.Provider>,
    );
    await screen.findByLabelText("Versión del contrato");
    return userEvent.setup();
  }

  function calcularBody() {
    const llamada = fetchFalso.mock.calls.find(([r, init]) => r === "/v1/reajuste/calcular" && init?.method === "POST");
    return llamada ? (JSON.parse(String(llamada[1]?.body)) as { componentes: Record<string, string>[]; ejecutado: Record<string, string>[] }) : undefined;
  }

  function pedidas(ruta: string): string[] {
    return fetchFalso.mock.calls.map(([u]) => String(u)).filter((u) => u.startsWith(ruta));
  }

  test("pide las series una vez y las partidas de la versión elegida, y las vuelve a pedir al cambiar de versión", async () => {
    const u = await montar();
    await waitFor(() => expect(pedidas("/v1/reajuste/partidas")).toEqual(["/v1/reajuste/partidas?proyecto=Contrato+S1&version=001"]));
    expect(pedidas("/v1/reajuste/series")).toEqual(["/v1/reajuste/series"]);
    await u.selectOptions(screen.getByLabelText("Versión del contrato"), "002");
    await waitFor(() => expect(pedidas("/v1/reajuste/partidas")).toContain("/v1/reajuste/partidas?proyecto=Contrato+S1&version=002"));
    expect(pedidas("/v1/reajuste/series")).toHaveLength(1);
  });

  test("«Serie» de un componente ofrece las series importadas y elegir con el teclado la escribe", async () => {
    const u = await montar();
    const campo = screen.getByLabelText("Serie, Componentes fila 1");
    expect(campo).toHaveAttribute("role", "combobox");
    await u.type(campo, "mater");
    const opcion = await screen.findByRole("option", { name: /Índice de materiales/ });
    expect(opcion).toHaveTextContent("FIC-MAT");
    expect(opcion).toHaveTextContent("BCV");
    expect(opcion).toHaveTextContent("indice_bs");
    expect(screen.queryByRole("option", { name: /equipos/ })).toBeNull();
    await u.keyboard("{ArrowDown}{Enter}");
    expect(campo).toHaveValue("FIC-MAT");
    await u.click(screen.getByRole("tab", { name: "2. Períodos y lo ejecutado" }));
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    await screen.findByRole("table", { name: "Escalatoria y comprobación, lado a lado" });
    expect(calcularBody()?.componentes[0]).toEqual({ componente: "materiales", serie: "FIC-MAT", peso: "" });
  });

  test("la lista de una celda va fuera de la tabla (portal) para que el desplazamiento no la recorte", async () => {
    const u = await montar();
    await u.type(screen.getByLabelText("Serie, Componentes fila 1"), "fic");
    const lista = await screen.findByRole("listbox", { name: "Serie, Componentes fila 1" });
    expect(within(screen.getByRole("table", { name: "Componentes" })).queryByRole("listbox")).toBeNull();
    expect(lista.closest(".silice-busqueda__panel--en-celda")).not.toBeNull();
    expect(lista.closest(".silice-busqueda__panel")).toHaveStyle({ position: "fixed" });
  });

  test("una serie que no se importó no se ofrece «tal cual»", async () => {
    const u = await montar();
    await u.type(screen.getByLabelText("Serie, Componentes fila 1"), "XYZ");
    expect(await screen.findByText(/No encontramos «XYZ»/)).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /tal cual/ })).toBeNull();
  });

  test("«Partida» de lo ejecutado ofrece las de la versión del contrato y elegir la escribe", async () => {
    const u = await montar();
    await u.click(screen.getByRole("tab", { name: "2. Períodos y lo ejecutado" }));
    const campo = await screen.findByLabelText("Partida, Ejecutado fila 1");
    expect(campo).toHaveAttribute("role", "combobox");
    await u.type(campo, "cuneta");
    const opcion = await screen.findByRole("option", { name: /Cuneta de concreto/ });
    expect(opcion).toHaveTextContent("S1-R02");
    expect(opcion).toHaveTextContent("m");
    expect(screen.queryByRole("option", { name: /Partida ficticia/ })).toBeNull();
    await u.click(opcion);
    expect(campo).toHaveValue("S1-R02");
    await u.type(screen.getByLabelText("Cantidad, Ejecutado fila 1"), "10");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    await screen.findByRole("table", { name: "Escalatoria y comprobación, lado a lado" });
    expect(calcularBody()?.ejecutado).toEqual([{ periodo: "1", partida: "S1-R02", cantidad: "10", fuente: "" }]);
  });

  test("una partida que no es de la versión elegida no se ofrece «tal cual»; con otra versión se ofrecen las de esa", async () => {
    const u = await montar();
    await u.click(screen.getByRole("tab", { name: "2. Períodos y lo ejecutado" }));
    const campo = await screen.findByLabelText("Partida, Ejecutado fila 1");
    await u.type(campo, "S1-R09");
    expect(await screen.findByText(/No encontramos «S1-R09»/)).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: /tal cual/ })).toBeNull();
    await u.selectOptions(screen.getByLabelText("Versión del contrato"), "002");
    await u.clear(campo);
    await u.type(campo, "S1-R09");
    expect(await screen.findByRole("option", { name: /Solo de la segunda/ })).toBeInTheDocument();
  });

  test("si la lista no se pudo leer, la serie y la partida siguen siendo de texto libre", async () => {
    series = () => json({ detalle: "No se pudo leer." }, 503);
    partidas = () => json({ detalle: "No se pudo leer." }, 503);
    const u = await montar();
    await u.type(screen.getByLabelText("Serie, Componentes fila 1"), "FIC-MAT");
    await u.click(screen.getByRole("tab", { name: "2. Períodos y lo ejecutado" }));
    await u.type(await screen.findByLabelText("Partida, Ejecutado fila 1"), "S1-R01");
    await u.type(screen.getByLabelText("Cantidad, Ejecutado fila 1"), "10");
    await u.click(screen.getByRole("button", { name: "Calcular" }));
    await screen.findByRole("table", { name: "Escalatoria y comprobación, lado a lado" });
    expect(calcularBody()?.componentes[0]?.serie).toBe("FIC-MAT");
    expect(calcularBody()?.ejecutado[0]?.partida).toBe("S1-R01");
  });

  test("los componentes siguen siendo tres filas fijas y el nombre de cada campo no cambia", async () => {
    await montar();
    expect(screen.getByLabelText("Componente, Componentes fila 1")).toHaveAttribute("readonly");
    expect(screen.getByLabelText("Serie, Componentes fila 2")).toBeInTheDocument();
    expect(screen.getByLabelText("Peso, Componentes fila 3")).toBeInTheDocument();
  });
});
