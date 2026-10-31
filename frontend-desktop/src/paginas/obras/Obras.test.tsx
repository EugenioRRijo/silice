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
    "aprobar_version",
    "cambiar_caso",
  ],
  modo_entrega: false,
};
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
    "activar_modulos",
    "cambiar_carpeta_de_datos",
  ],
};

describe("Inicio de presupuestos y obras: «Lo que puede hacer aquí» (quien no lee obras)", () => {
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

  // Los enlaces (href) de las pantallas de la lista: las que la cuenta puede usar y no tienen sitio en la barra lateral.
  function accesos(): string[] {
    const region = screen.getByRole("region", { name: "Lo que puede hacer aquí" });
    return [...region.querySelectorAll("a")].map((a) => a.getAttribute("href") ?? "");
  }

  test("admin ve el h1 y, sin sitio en la barra lateral, «Inicio de producción», «Receta de la planta», «Producir mezcla», «Precios de la empresa» e «Índices del BCV»", () => {
    montar(ADMIN);
    expect(screen.getByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" })).toHaveClass("cds--type-heading-04");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(accesos()).toEqual(["/precios_empresa", "/indices", "/produccion", "/receta_planta", "/producir_mezcla"]);
    expect(screen.getByRole("link", { name: "Precios de la empresa" })).toHaveAccessibleDescription(
      "Cargue y cree las listas de precios de la empresa",
    );
    expect(screen.getByRole("link", { name: "Índices del BCV" })).toHaveAccessibleDescription(
      "Cargue los índices publicados por el BCV",
    );
    expect(screen.getByText("Cargue los índices publicados por el BCV")).toBeVisible();
  });

  test("el único encabezado es su h2 y la lista no son mosaicos", () => {
    montar(ADMIN);
    const region = screen.getByRole("region", { name: "Lo que puede hacer aquí" });
    expect(within(region).getAllByRole("heading").map((h) => [h.tagName, h.textContent])).toEqual([["H2", "Lo que puede hacer aquí"]]);
    expect(within(region).getByRole("heading", { level: 2 })).toHaveClass("cds--type-heading-compact-02");
    expect(region.querySelector(".cds--tile")).toBeNull();
    expect(within(region).getByRole("list", { name: "Lo que puede hacer aquí" })).toBeInTheDocument();
  });

  test("pulsar un acceso abre su pantalla", async () => {
    const usuario = userEvent.setup();
    montar(ADMIN);
    await usuario.click(screen.getByRole("link", { name: "Precios de la empresa" }));
    expect(await screen.findByRole("heading", { name: "Pantalla de precios" })).toBeInTheDocument();
  });

  test("el administrador no pide la mesa (la API le daría 403) ni ve «Nueva obra»", () => {
    montar(ADMIN);
    expect(fetchFalso).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Nueva obra" })).toBeNull();
  });

  test("quien arma no ve los accesos: ve la mesa", () => {
    montar(ANA);
    expect(screen.queryByRole("region", { name: "Lo que puede hacer aquí" })).toBeNull();
    expect(screen.getByRole("heading", { level: 2, name: "Cómo van las obras" })).toBeInTheDocument();
  });
});
