import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import CostoPorTonelada from "./CostoPorTonelada";

// Datos ficticios. Los cálculos anteriores se leen del servidor tal como se guardaron; la pantalla solo les da formato.
const ANA: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["operar_arenera", "registrar_costos_produccion"],
  modo_entrega: false,
};
const ADMIN: SesionRespuesta = { ...ANA, login: "admin", roles: ["administrador"], acciones: [...ANA.acciones, "publicar_costo_propio"] };

const PUBLICADO = { lista_id: 12, caso: "Obra ficticia", registrado: "2026-12-01T09:30:00" };
const RESUMENES = [
  { id: 8, periodo: "2026-11", moneda: "Bs", usuario: "ana", registrado: "2026-12-01T08:00:00", huella: "b".repeat(64), publicado: PUBLICADO },
  { id: 7, periodo: "2026-11", moneda: "USD", usuario: "ana", registrado: "2026-11-30T10:00:00", huella: "a".repeat(64), publicado: null },
];
function calculo(id: number, moneda: string, publicado: typeof PUBLICADO | null) {
  return {
    id,
    periodo: "2026-11",
    moneda,
    huella: "a".repeat(64),
    usuario: "ana",
    registrado: "2026-11-30T10:00:00",
    productos: [{ codigo: "MZP-01", por_tonelada: "50.700123", presentado: "50.70" }],
    instantanea: { entradas: { agregados: [], producido: {} }, resultado: { total_cantera: "0", total_planta: "1200" } },
    publicado,
  };
}
const EMPRESA = { empresa: { nombre: "Constructora Ficticia, C.A.", rif: "J-00000000-0", ciudad: "Valencia" }, clave: null, sensible: {} };

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

describe("Cálculos anteriores", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let publicacion: () => Response;
  let usuario: ReturnType<typeof userEvent.setup>;
  const alExpirar = vi.fn();

  function montar(sesion: SesionRespuesta = ANA) {
    render(
      <ContextoAplicacion.Provider value={{ sesion, proyecto: null, caso: null, recargarProyectos: vi.fn(), alExpirar }}>
        <MemoryRouter>
          <CostoPorTonelada />
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  const lecturas = (ruta: string) => fetchFalso.mock.calls.filter((c) => String(c[0]) === ruta && (c[1]?.method ?? "GET") === "GET").length;

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 11, 15, 10, 0, 0));
    usuario = userEvent.setup();
    fijarCsrf("tok");
    alExpirar.mockReset();
    fetchFalso.mockReset();
    vi.stubGlobal("fetch", fetchFalso);
    publicacion = () => json({ id: 12, nombre: "Costo propio 2026-11, cálculo n.º 7" }, 201);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      const metodo = init?.method ?? "GET";
      if (url.pathname === "/v1/produccion/producido") return json([]);
      if (url.pathname === "/v1/produccion/calculos" && metodo === "GET") return json(RESUMENES);
      if (url.pathname === "/v1/produccion/calculos/8") return json(calculo(8, "Bs", PUBLICADO));
      if (url.pathname === "/v1/produccion/calculos/7" && metodo === "GET") return json(calculo(7, "USD", null));
      if (url.pathname === "/v1/produccion/calculos/7/publicar" && metodo === "POST") return publicacion();
      if (url.pathname === "/v1/admin/empresa") return json(EMPRESA);
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  test("lista los cálculos del período con su fecha es-VE y si se publicaron", async () => {
    montar();
    const lista = await screen.findByRole("list", { name: "Cálculos anteriores de noviembre de 2026" });
    const [primero, segundo] = within(lista).getAllByRole("listitem");
    expect(primero).toHaveTextContent("Cálculo n.º 8");
    expect(primero).toHaveTextContent("01/12/2026");
    expect(primero).toHaveTextContent("Bs");
    expect(primero).toHaveTextContent("Publicado en la lista n.º 12");
    expect(segundo).toHaveTextContent("Cálculo n.º 7");
    expect(segundo).toHaveTextContent("30/11/2026");
    expect(segundo).toHaveTextContent("Sin publicar");
    expect(fetchFalso.mock.calls.some((c) => String(c[0]) === "/v1/produccion/calculos?periodo=2026-11")).toBe(true);
  });

  test("sin cálculos en el mes lo dice", async () => {
    fetchFalso.mockImplementation(async (entrada) => {
      const url = new URL(String(entrada), "http://prueba");
      return url.pathname === "/v1/produccion/calculos" ? json([]) : json([]);
    });
    montar();
    expect(await screen.findByText("Todavía no se calculó este mes.")).toBeInTheDocument();
  });

  test("abrir uno muestra su costo por tonelada y su fuente", async () => {
    montar();
    await usuario.click(await screen.findByRole("button", { name: "Abrir el cálculo n.º 7" }));
    const resultado = await screen.findByRole("region", { name: "Resultado del cálculo" });
    expect(within(resultado).getByRole("row", { name: /MZP-01/ })).toHaveTextContent("50,70");
    expect(within(resultado).getByText("Producción, período 2026-11, cálculo n.º 7")).toBeInTheDocument();
    await waitFor(() => expect(document.activeElement).toBe(resultado));
  });

  test("Publicar no aparece en uno ya publicado y dice en qué lista quedó", async () => {
    montar(ADMIN);
    await usuario.click(await screen.findByRole("button", { name: "Abrir el cálculo n.º 8" }));
    const resultado = await screen.findByRole("region", { name: "Resultado del cálculo" });
    expect(within(resultado).queryByRole("button", { name: /Publicar/ })).not.toBeInTheDocument();
    expect(within(resultado).getByText(/Ya se publicó en la lista n\.º 12/)).toBeInTheDocument();
    expect(within(resultado).getByText(/01\/12\/2026/)).toBeInTheDocument();
  });

  test("uno sin publicar sí ofrece Publicar al administrador", async () => {
    montar(ADMIN);
    await usuario.click(await screen.findByRole("button", { name: "Abrir el cálculo n.º 7" }));
    const resultado = await screen.findByRole("region", { name: "Resultado del cálculo" });
    expect(await within(resultado).findByRole("button", { name: "Publicar como precio propio" })).toBeEnabled();
  });

  test("un 409 al publicar se muestra con su texto y recarga la lista", async () => {
    publicacion = () => json({ detalle: "El cálculo n.º 7 ya se publicó en la lista n.º 12." }, 409);
    montar(ADMIN);
    await usuario.click(await screen.findByRole("button", { name: "Abrir el cálculo n.º 7" }));
    const resultado = await screen.findByRole("region", { name: "Resultado del cálculo" });
    await within(resultado).findByText("Constructora Ficticia, C.A. (J-00000000-0)");
    const antes = lecturas("/v1/produccion/calculos?periodo=2026-11");
    await usuario.click(within(resultado).getByRole("button", { name: "Publicar como precio propio" }));
    await usuario.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Publicar" }));
    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("El cálculo n.º 7 ya se publicó en la lista n.º 12.");
    await waitFor(() => expect(lecturas("/v1/produccion/calculos?periodo=2026-11")).toBe(antes + 1));
    await waitFor(() => expect(alerta.closest("[tabindex]")).toBe(document.activeElement));
  });

  test("al publicar con éxito el aviso recibe el foco y la lista se recarga", async () => {
    montar(ADMIN);
    await usuario.click(await screen.findByRole("button", { name: "Abrir el cálculo n.º 7" }));
    const resultado = await screen.findByRole("region", { name: "Resultado del cálculo" });
    await within(resultado).findByText("Constructora Ficticia, C.A. (J-00000000-0)");
    const antes = lecturas("/v1/produccion/calculos?periodo=2026-11");
    await usuario.click(within(resultado).getByRole("button", { name: "Publicar como precio propio" }));
    await usuario.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Publicar" }));
    const aviso = await screen.findByText('Publicado: lista "Costo propio 2026-11, cálculo n.º 7".');
    await waitFor(() => expect(document.activeElement).toBe(aviso.closest("[tabindex]")));
    await waitFor(() => expect(lecturas("/v1/produccion/calculos?periodo=2026-11")).toBe(antes + 1));
  });
});
