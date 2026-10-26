import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import PaginaObras from "./index";

// Acciones por rol escritas a mano desde seguridad/permisos.py.
const ANA: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: [
    "editar_hoja",
    "convertir_y_reajustar",
    "control_de_obra",
    "decidir_recuperacion",
    "entregar_paquete",
    "operar_arenera",
    "leer_proyecto",
    "cambiar_caso",
  ],
  modo_entrega: false,
};
const RITA: SesionRespuesta = { ...ANA, login: "rita", nombre: "Rita Gómez", roles: ["revisa"], acciones: ["leer_proyecto", "revisar_paquete"] };
const ADMIN: SesionRespuesta = {
  ...ANA,
  login: "admin",
  nombre: "Administración Demo",
  roles: ["administrador"],
  acciones: [
    "operar_arenera",
    "cambiar_caso",
    "administrar_cuentas",
    "administrar_empresa",
    "administrar_precios",
    "administrar_red_y_api",
    "cambiar_carpeta_de_datos",
  ],
};

describe("Inicio de presupuestos y obras (accesos del módulo)", () => {
  const fetchFalso = vi.fn<typeof fetch>();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fetchFalso.mockImplementation(async () => new Response(JSON.stringify({ detalle: "No encontrado." }), { status: 404 }));
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function montar(sesion: SesionRespuesta) {
    const valor: Aplicacion = {
      sesion,
      proyecto: null,
      caso: { nombre: "clinica", ruta_relativa: "data/clinica.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
      modulo: "obras",
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <MemoryRouter initialEntries={["/obras"]}>
          <Routes>
            <Route path="/obras" element={<PaginaObras />} />
            <Route path="/precios_empresa" element={<h1>Pantalla de precios</h1>} />
          </Routes>
        </MemoryRouter>
      </ContextoAplicacion.Provider>,
    );
  }

  // Los rotulos de area y, debajo de cada uno, los enlaces (href) de sus pantallas.
  function accesos(): [string, string[]][] {
    const region = screen.getByRole("region", { name: "Pantallas del módulo" });
    return [...region.querySelectorAll<HTMLElement>(".silice-accesos__area")].map((area) => [
      area.querySelector(".silice-accesos__rotulo")?.textContent ?? "",
      [...area.querySelectorAll("a")].map((a) => a.getAttribute("href") ?? ""),
    ]);
  }

  test("admin ve el h1 y los accesos «Precios de la empresa» e «Índices del BCV» con su línea de ayuda", () => {
    montar(ADMIN);
    expect(screen.getByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" })).toHaveClass("cds--type-heading-04");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(accesos()).toEqual([["Mercado", ["/precios_empresa", "/indices"]]]);
    expect(screen.getByRole("link", { name: "Precios de la empresa" })).toHaveAccessibleDescription(
      "Cargue y cree las listas de precios de la empresa",
    );
    expect(screen.getByRole("link", { name: "Índices del BCV" })).toHaveAccessibleDescription(
      "Cargue los índices publicados por el BCV",
    );
    expect(screen.getByText("Cargue los índices publicados por el BCV")).toBeVisible();
  });

  test("ana ve sus pantallas agrupadas por área, sin el propio inicio", () => {
    montar(ANA);
    expect(accesos()).toEqual([
      ["Obras", ["/hoja", "/elaborar", "/tablero", "/entregar"]],
      ["Partidas", ["/componer", "/catalogo", "/similares"]],
      ["Mercado", ["/actualizacion", "/historico", "/simulador"]],
      ["Control", ["/control", "/reajuste", "/escenarios"]],
    ]);
    expect(screen.queryByRole("link", { name: /Inicio de presupuestos y obras/ })).not.toBeInTheDocument();
  });

  test("en modo entrega no aparece ninguna pantalla de Investigación", () => {
    montar({ ...ANA, modo_entrega: true });
    const todas = accesos().flatMap(([, hrefs]) => hrefs);
    for (const fuera of ["/similares", "/simulador", "/escenarios"]) expect(todas).not.toContain(fuera);
  });

  test("rita ve Tablero, Catálogo e Histórico, cada uno bajo su área", () => {
    montar(RITA);
    expect(accesos()).toEqual([
      ["Obras", ["/tablero"]],
      ["Partidas", ["/catalogo"]],
      ["Mercado", ["/historico"]],
    ]);
  });

  test("los rótulos de área son texto (no encabezados) y la lista no son mosaicos", () => {
    montar(ANA);
    const region = screen.getByRole("region", { name: "Pantallas del módulo" });
    // El único encabezado es el h2 de la sección; los rótulos de área no lo son.
    expect(within(region).getAllByRole("heading").map((h) => [h.tagName, h.textContent])).toEqual([["H2", "Pantallas del módulo"]]);
    expect(within(region).getByRole("heading", { level: 2 })).toHaveClass("cds--type-heading-compact-02");
    expect(region.querySelector(".cds--tile")).toBeNull();
    // Cada área es una lista de enlaces con nombre propio.
    expect(within(region).getByRole("list", { name: "Partidas" })).toBeInTheDocument();
  });

  test("pulsar un acceso abre su pantalla", async () => {
    const usuario = userEvent.setup();
    montar(ADMIN);
    await usuario.click(screen.getByRole("link", { name: "Precios de la empresa" }));
    expect(await screen.findByRole("heading", { name: "Pantalla de precios" })).toBeInTheDocument();
  });

  test("no pide nada a la API (las cifras de la mesa llegan en otra tarea)", () => {
    montar(ANA);
    expect(fetchFalso).not.toHaveBeenCalled();
  });
});
