import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaProduccion from "./index";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), {
    status: estado,
    headers: { "Content-Type": "application/json" },
  });
}

// Acciones a mano de seguridad/permisos.py: operan la arenera quien arma y el administrador.
const ANA: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto", "operar_arenera"],
  modo_entrega: false,
};
const ADMIN: SesionRespuesta = {
  ...ANA,
  login: "admin",
  nombre: "Administración Demo",
  roles: ["administrador"],
  acciones: ["administrar_cuentas", "operar_arenera", "cambiar_caso"],
};

function existencia(codigo: string, parcial: Record<string, unknown> = {}) {
  return {
    codigo,
    nombre: `Material ${codigo}`,
    unidad_venta: "m3",
    existencia: "120.5",
    minima: "50",
    queda_poco: false,
    negativa: false,
    ...parcial,
  };
}

describe("Inicio de producción", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let existencias: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    existencias = () => json([existencia("ARENA")]);
    fetchFalso.mockImplementation(async (entrada) => {
      const ruta = String(entrada);
      if (ruta === "/v1/produccion/existencias") return existencias();
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function montar(aplicacion: Partial<Aplicacion> = {}) {
    const valor: Aplicacion = {
      sesion: ANA,
      proyecto: null,
      caso: { nombre: "clinica", ruta_relativa: "data/clinica.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
      ...aplicacion,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter initialEntries={["/produccion"]}>
          <Routes>
            <Route path="/produccion" element={<PaginaProduccion />} />
            <Route path="/existencias" element={<h1>Pantalla de existencias</h1>} />
          </Routes>
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  function rutasPedidas(): string[] {
    return fetchFalso.mock.calls.map((c) => String(c[0]));
  }

  test.each([
    ["ana", ANA],
    ["admin", ADMIN],
  ] as const)("con %s: h1 «Inicio de producción» y el panel de la arenera; solo pide la arenera", async (_, sesion) => {
    montar({ sesion });
    expect(screen.getByRole("heading", { level: 1, name: "Inicio de producción" })).toHaveClass("cds--type-heading-04");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(await screen.findByRole("region", { name: "Arenera: lo que requiere atención" })).toBeInTheDocument();
    expect(await screen.findByText("Todo sobre el mínimo")).toBeInTheDocument();
    expect(rutasPedidas()).toEqual(["/v1/produccion/existencias"]);
    expect(screen.queryByText("Herramientas principales")).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Audite un presupuesto" })).not.toBeInTheDocument();
  });

  test("lista solo lo que pide atención, lo negativo primero, con ícono y texto", async () => {
    existencias = () =>
      json([
        existencia("ARENA"),
        existencia("PIEDRA", { existencia: "30", minima: "50", queda_poco: true }),
        existencia("GRAVA", { existencia: "-4.5", minima: "20", queda_poco: true, negativa: true }),
      ]);
    montar();
    const seccion = await screen.findByRole("region", { name: "Arenera: lo que requiere atención" });
    const filas = within(seccion).getAllByRole("row").slice(1); // sin el encabezado
    expect(filas).toHaveLength(2);
    expect(filas[0]).toHaveTextContent("Material GRAVA");
    expect(filas[0]).toHaveTextContent("-4.5 m3");
    expect(filas[0]).toHaveTextContent("Existencia negativa: falta registrar producción o conteo");
    expect(filas[1]).toHaveTextContent("Material PIEDRA");
    expect(filas[1]).toHaveTextContent("Queda poco");
    expect(within(seccion).queryByText("Material ARENA")).not.toBeInTheDocument();
    expect(filas[0].querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    expect(within(seccion).getByRole("link", { name: "Ver todas las existencias" })).toHaveAttribute("href", "/existencias");
  });

  test("muestra el mínimo junto a la existencia, con las cifras tal como vienen", async () => {
    existencias = () => json([existencia("PIEDRA", { existencia: "30.00", minima: "50.000", queda_poco: true })]);
    montar();
    const seccion = await screen.findByRole("region", { name: "Arenera: lo que requiere atención" });
    expect(within(seccion).getByText("30.00 m3")).toBeInTheDocument();
    expect(within(seccion).getByText("50.000 m3")).toBeInTheDocument();
  });

  test("sin materiales, enseña a registrarlos y enlaza a Existencias", async () => {
    existencias = () => json([]);
    const usuario = userEvent.setup();
    montar();
    expect(await screen.findByText("Aún no hay materiales")).toBeInTheDocument();
    await usuario.click(screen.getByRole("link", { name: "Registrar materiales en Producción" }));
    expect(await screen.findByRole("heading", { name: "Pantalla de existencias" })).toBeInTheDocument();
  });

  test("mientras carga, la arenera lo dice", () => {
    fetchFalso.mockImplementation(() => new Promise<Response>(() => {}));
    montar();
    expect(screen.getByLabelText("Cargando la arenera")).toHaveAttribute("aria-busy", "true");
  });

  test("si la arenera aún no existe en la API (404), avisa sin romper la página", async () => {
    existencias = () => json({ detalle: "No encontrado." }, 404);
    montar();
    expect(await screen.findByText("Sin datos de la arenera en esta instalación")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  test("una respuesta 401 avisa que la sesión venció y deja el bloque en error", async () => {
    const alExpirar = vi.fn();
    existencias = () => json({ detalle: "Sesión vencida." }, 401);
    montar({ alExpirar });
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
    expect(await screen.findByRole("alert")).toHaveTextContent("Sesión vencida.");
  });

  test("otro error de la API se muestra con su detalle", async () => {
    existencias = () => json({ detalle: "La base de la instalación no responde." }, 500);
    montar();
    expect(await screen.findByRole("alert")).toHaveTextContent("La base de la instalación no responde.");
  });

  test("quien registra costos ve el paso a «Costos del período»; quien no, no", async () => {
    const conCostos = { ...ANA, acciones: [...ANA.acciones, "registrar_costos_produccion"] };
    const { unmount } = montar({ sesion: conCostos });
    expect(await screen.findByRole("link", { name: "Costos del período" })).toHaveAttribute("href", "/costos");
    unmount();
    montar({ sesion: ANA });
    await screen.findByRole("region", { name: "Arenera: lo que requiere atención" });
    expect(screen.queryByRole("link", { name: "Costos del período" })).not.toBeInTheDocument();
  });
});
