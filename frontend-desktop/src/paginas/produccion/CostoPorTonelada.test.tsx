import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import CostoPorTonelada from "./CostoPorTonelada";

// Datos ficticios. El servidor manda los montos como texto con punto (exacto y presentado); la pantalla no calcula
// ninguno: solo les da formato.
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

const CALCULO = {
  id: 7,
  periodo: "2026-11",
  moneda: "USD",
  huella: "a".repeat(64),
  usuario: "ana",
  registrado: "2026-11-30T10:00:00",
  productos: [
    { codigo: "AGR-12", por_tonelada: "5", presentado: "5.00" },
    { codigo: "MZP-01", por_tonelada: "50.700123", presentado: "50.70" },
  ],
  instantanea: {
    entradas: { agregados: ["AGR-12"], producido: { "AGR-12": "150", "MZP-01": "100" } },
    resultado: { total_cantera: "750", total_planta: "1200", planta_por_t: "12", por_tonelada: {} },
  },
};
const EMPRESA = { empresa: { nombre: "Constructora Ficticia, C.A.", rif: "J-00000000-0", ciudad: "Valencia" }, clave: null, sensible: {} };

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

describe("Costo por tonelada", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let producido: () => Response;
  let calculo: () => Response;
  let publicacion: () => Response;
  let empresa: () => Response;
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

  const posts = () =>
    fetchFalso.mock.calls
      .filter((c) => c[1]?.method === "POST")
      .map((c) => ({ ruta: String(c[0]), cuerpo: c[1]?.body ? JSON.parse(String(c[1].body)) : null }));

  async function calcular(moneda = "USD") {
    await screen.findByText(/AGR-12: 150 t/);
    await usuario.selectOptions(screen.getByLabelText("Moneda del cálculo"), moneda);
    await usuario.click(screen.getByRole("button", { name: "Calcular costo por tonelada" }));
    return screen.findByRole("region", { name: "Resultado del cálculo" });
  }

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date(2026, 11, 15, 10, 0, 0)); // el mes por defecto es el anterior: 2026-11
    usuario = userEvent.setup();
    fijarCsrf("tok");
    alExpirar.mockReset();
    fetchFalso.mockReset();
    vi.stubGlobal("fetch", fetchFalso);
    producido = () =>
      json([
        { codigo: "AGR-12", toneladas: "150" },
        { codigo: "MZP-01", toneladas: "100" },
      ]);
    calculo = () => json(CALCULO, 201);
    publicacion = () => json({ id: 12, nombre: "Costo propio 2026-11, cálculo n.º 7" }, 201);
    empresa = () => json(EMPRESA);
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = new URL(String(entrada), "http://prueba");
      const metodo = init?.method ?? "GET";
      if (url.pathname === "/v1/produccion/producido" && metodo === "GET") return producido();
      if (url.pathname === "/v1/produccion/calculos" && metodo === "POST") return calculo();
      if (url.pathname === "/v1/produccion/calculos" && metodo === "GET") return json([]); // Tarea 6b: cálculos anteriores
      if (url.pathname === "/v1/produccion/calculos/7/publicar" && metodo === "POST") return publicacion();
      if (url.pathname === "/v1/admin/empresa" && metodo === "GET") return empresa();
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  test("tiene un solo h1 y muestra lo producido en el mes, tal como lo manda el servidor", async () => {
    montar();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("heading", { level: 1, name: "Costo por tonelada" })).toBeInTheDocument();
    expect(await screen.findByText("AGR-12: 150 t")).toBeInTheDocument();
    expect(screen.getByText("MZP-01: 100 t")).toBeInTheDocument();
    expect(fetchFalso.mock.calls.map((c) => String(c[0]))).toContain("/v1/produccion/producido?periodo=2026-11");
  });

  test("el mes arranca en el mes anterior, ya cerrado, no en el que corre", async () => {
    montar();
    await screen.findByText("AGR-12: 150 t");
    expect(screen.getByLabelText("Mes")).toHaveValue("2026-11");
  });

  test("la moneda no tiene valor por defecto: sin elegirla no se calcula y el campo dice por qué", async () => {
    montar();
    await screen.findByText("AGR-12: 150 t");
    const campo = screen.getByLabelText("Moneda del cálculo");
    expect(campo).toHaveValue("");
    // Hallazgo 12 del recorrido: el botón inactivo no decía por qué. Ahora se pulsa y el campo se marca con su error.
    const boton = screen.getByRole("button", { name: "Calcular costo por tonelada" });
    expect(boton).toBeEnabled();
    await usuario.click(boton);
    expect(posts()).toHaveLength(0);
    expect(campo).toHaveAttribute("aria-invalid", "true");
    expect(campo).toHaveAccessibleDescription("Elija la moneda del cálculo: no tiene valor por defecto.");
    expect(campo).toHaveFocus();
    // Al elegirla, el error se va y el cálculo sale.
    await usuario.selectOptions(campo, "USD");
    expect(campo).not.toHaveAttribute("aria-invalid", "true");
    await usuario.click(boton);
    expect(posts()).toEqual([{ ruta: "/v1/produccion/calculos", cuerpo: { periodo: "2026-11", moneda: "USD" } }]);
  });

  test("el cálculo muestra costo por tonelada por producto y su fuente", async () => {
    montar();
    const resultado = await calcular();
    expect(posts()).toEqual([{ ruta: "/v1/produccion/calculos", cuerpo: { periodo: "2026-11", moneda: "USD" } }]);
    expect(within(resultado).getByRole("row", { name: /AGR-12/ })).toHaveTextContent("5,00");
    const mezcla = within(resultado).getByRole("row", { name: /MZP-01/ });
    expect(mezcla).toHaveTextContent("50,70");
    // El exacto se lee en su propia columna, no solo en un título.
    expect(mezcla).toHaveTextContent("50,700123");
    expect(within(resultado).getByText("Producción, período 2026-11, cálculo n.º 7")).toBeInTheDocument();
    expect(within(resultado).getByRole("columnheader", { name: /Costo por tonelada \(USD\)/ })).toBeInTheDocument();
    expect(within(resultado).getByText(/Total de la cantera: 750,00 USD/)).toBeInTheDocument();
    // El foco queda en el resultado, no en BODY.
    await waitFor(() => expect(document.activeElement).toBe(resultado));
  });

  test("el precio es el del servidor: la pantalla no recalcula nada", async () => {
    calculo = () =>
      json({ ...CALCULO, productos: [{ codigo: "MZP-01", por_tonelada: "99999.999", presentado: "100000.00" }] }, 201);
    montar();
    const resultado = await calcular();
    expect(within(resultado).getByRole("row", { name: /MZP-01/ })).toHaveTextContent("100.000,00");
    expect(within(resultado).getByRole("row", { name: /MZP-01/ })).toHaveTextContent("99.999,999");
  });

  test("un error de tasa faltante lista cada costo con su fecha", async () => {
    calculo = () =>
      json(
        {
          detalle:
            "No hay tasa del BCV del mismo día para convertir a USD: costo n.º 7 del 07/11/2026; costo n.º 9 del 08/11/2026. " +
            "Cárguela en Índices y vuelva a calcular; no se calculó nada.",
        },
        422,
      );
    montar();
    await screen.findByText("AGR-12: 150 t");
    await usuario.selectOptions(screen.getByLabelText("Moneda del cálculo"), "USD");
    await usuario.click(screen.getByRole("button", { name: "Calcular costo por tonelada" }));
    const alerta = await screen.findByRole("alert");
    const items = within(alerta).getAllByRole("listitem");
    expect(items.map((i) => i.textContent)).toEqual(["costo n.º 7 del 07/11/2026", "costo n.º 9 del 08/11/2026"]);
    expect(alerta).toHaveTextContent("Cárguela en Índices");
    expect(alerta).not.toHaveTextContent(/UC-|422/);
    expect(screen.queryByRole("region", { name: "Resultado del cálculo" })).not.toBeInTheDocument();
    await waitFor(() => expect(alerta.closest("[tabindex]")).toBe(document.activeElement));
  });

  test.each([
    ["Este cálculo no tiene costos por tonelada que publicar.", 422],
    ["No hay costos registrados en 2026-11.", 422],
  ])("el rechazo «%s» se muestra tal cual", async (detalle, estado) => {
    calculo = () => json({ detalle }, estado);
    montar();
    await screen.findByText("AGR-12: 150 t");
    await usuario.selectOptions(screen.getByLabelText("Moneda del cálculo"), "Bs");
    await usuario.click(screen.getByRole("button", { name: "Calcular costo por tonelada" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(detalle);
  });

  test("un 403 se lee como falta de permiso", async () => {
    calculo = () => json({ detalle: "Forbidden" }, 403);
    montar();
    await screen.findByText("AGR-12: 150 t");
    await usuario.selectOptions(screen.getByLabelText("Moneda del cálculo"), "Bs");
    await usuario.click(screen.getByRole("button", { name: "Calcular costo por tonelada" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Su cuenta no tiene permiso para esta acción.");
  });

  test("un 401 avisa a la aplicación", async () => {
    calculo = () => json({ detalle: "Sesión vencida" }, 401);
    montar();
    await screen.findByText("AGR-12: 150 t");
    await usuario.selectOptions(screen.getByLabelText("Moneda del cálculo"), "Bs");
    await usuario.click(screen.getByRole("button", { name: "Calcular costo por tonelada" }));
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("cambiar de mes o de moneda retira un resultado que ya no corresponde", async () => {
    montar();
    const resultado = await calcular();
    await usuario.selectOptions(screen.getByLabelText("Moneda del cálculo"), "Bs");
    expect(resultado).not.toBeInTheDocument();
  });

  test("Publicar solo aparece con la acción", async () => {
    montar(ANA);
    await calcular();
    expect(screen.queryByRole("button", { name: /Publicar/ })).not.toBeInTheDocument();
    expect(fetchFalso.mock.calls.some((c) => String(c[0]) === "/v1/admin/empresa")).toBe(false);
  });

  test("Publicar muestra la fuente con que quedará el precio y la empresa de Administración", async () => {
    montar(ADMIN);
    const resultado = await calcular();
    const seccion = within(resultado).getByRole("group", { name: "Publicar como precio propio" });
    expect(await within(seccion).findByText("Constructora Ficticia, C.A. (J-00000000-0)")).toBeInTheDocument();
    expect(within(seccion).getByText("Producción, período 2026-11, cálculo n.º 7")).toBeInTheDocument();
    expect(within(seccion).getByRole("button", { name: "Publicar como precio propio" })).toBeEnabled();
  });

  test("pide confirmación y publica sin cuerpo; el foco queda en el aviso", async () => {
    montar(ADMIN);
    const resultado = await calcular();
    await within(resultado).findByText("Constructora Ficticia, C.A. (J-00000000-0)");
    await usuario.click(within(resultado).getByRole("button", { name: "Publicar como precio propio" }));
    const dialogo = screen.getByRole("dialog", { name: "Publicar el costo propio" });
    expect(dialogo).toHaveTextContent('Se creará la lista "Costo propio 2026-11, cálculo n.º 7"');
    expect(posts().filter((p) => p.ruta.endsWith("/publicar"))).toHaveLength(0);
    await usuario.click(within(dialogo).getByRole("button", { name: "Publicar" }));
    await waitFor(() => expect(posts().filter((p) => p.ruta.endsWith("/publicar"))).toHaveLength(1));
    expect(posts().find((p) => p.ruta.endsWith("/publicar"))).toEqual({ ruta: "/v1/produccion/calculos/7/publicar", cuerpo: null });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    const aviso = await screen.findByText('Publicado: lista "Costo propio 2026-11, cálculo n.º 7".');
    await waitFor(() => expect(document.activeElement).toBe(aviso.closest("[tabindex]")));
  });

  test("un 403 al publicar dice que solo un administrador con sesión puede publicar", async () => {
    publicacion = () => json({ detalle: "Administrar la instalación requiere clave." }, 403);
    montar(ADMIN);
    const resultado = await calcular();
    await usuario.click(within(resultado).getByRole("button", { name: "Publicar como precio propio" }));
    const dialogo = screen.getByRole("dialog", { name: "Publicar el costo propio" });
    await usuario.click(within(dialogo).getByRole("button", { name: "Publicar" }));
    expect(await within(dialogo).findByRole("alert")).toHaveTextContent(
      "Solo un administrador con sesión puede publicar el costo propio.",
    );
  });

  test("un 401 al leer la empresa avisa a la aplicación", async () => {
    empresa = () => json({ detalle: "Sesión vencida" }, 401);
    montar(ADMIN);
    await calcular();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("cancelar no publica y Esc devuelve el foco al botón", async () => {
    montar(ADMIN);
    const resultado = await calcular();
    const boton = within(resultado).getByRole("button", { name: "Publicar como precio propio" });
    await usuario.click(boton);
    await usuario.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(document.activeElement).toBe(boton);
    expect(posts().filter((p) => p.ruta.endsWith("/publicar"))).toHaveLength(0);
  });

  test("sin empresa configurada, el 422 se muestra con el camino a Administración", async () => {
    publicacion = () => json({ detalle: "Configure la empresa en Administración antes de publicar." }, 422);
    montar(ADMIN);
    const resultado = await calcular();
    await usuario.click(within(resultado).getByRole("button", { name: "Publicar como precio propio" }));
    const dialogo = screen.getByRole("dialog", { name: "Publicar el costo propio" });
    await usuario.click(within(dialogo).getByRole("button", { name: "Publicar" }));
    const alerta = await within(dialogo).findByRole("alert");
    expect(alerta).toHaveTextContent("Configure la empresa en Administración antes de publicar.");
    expect(within(dialogo).getByRole("link", { name: "Ir a Administración" })).toHaveAttribute("href", "/empresa/personas");
  });

  test("un código de insumo de más de 20 caracteres se niega con el mensaje del servidor", async () => {
    publicacion = () =>
      json({ detalle: "El código de insumo MZP-MEZCLA-ASFALTICA-CALIENTE-01 pasa de 20 caracteres: acórtelo antes de publicar." }, 422);
    montar(ADMIN);
    const resultado = await calcular();
    await usuario.click(within(resultado).getByRole("button", { name: "Publicar como precio propio" }));
    await usuario.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Publicar" }));
    expect(await within(screen.getByRole("dialog")).findByRole("alert")).toHaveTextContent("pasa de 20 caracteres");
  });

  test("si no puede leer la empresa de Administración no la muestra y lo dice", async () => {
    empresa = () => json({ detalle: "Prohibido" }, 403);
    montar(ADMIN);
    const resultado = await calcular();
    expect(await within(resultado).findByText(/No se pudo leer la empresa de Administración/)).toBeInTheDocument();
    expect(within(resultado).queryByText(/Constructora/)).not.toBeInTheDocument();
  });

  test("sin empresa en Administración avisa antes de publicar, con el camino", async () => {
    empresa = () => json({ empresa: null, clave: null, sensible: {} });
    montar(ADMIN);
    const resultado = await calcular();
    expect(await within(resultado).findByText(/Todavía no se configuró la empresa/)).toBeInTheDocument();
    expect(within(resultado).getByRole("link", { name: "Ir a Administración" })).toHaveAttribute("href", "/empresa/personas");
  });

  test("un 409 al calcular no se rotula «No se pudo publicar el costo»", async () => {
    calculo = () => json({ detalle: "Conflicto al calcular." }, 409);
    montar();
    await screen.findByText("AGR-12: 150 t");
    await usuario.selectOptions(screen.getByLabelText("Moneda del cálculo"), "Bs");
    await usuario.click(screen.getByRole("button", { name: "Calcular costo por tonelada" }));
    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("No se pudo calcular el costo");
    expect(alerta).not.toHaveTextContent("No se pudo publicar el costo");
  });
});
