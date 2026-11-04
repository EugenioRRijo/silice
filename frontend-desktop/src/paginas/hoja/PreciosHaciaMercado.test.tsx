import { configure, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import type { ObraAbierta } from "../../marco/obraAbierta";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { atipicosRespuesta, cuerpoDeVista, preciosRespuesta } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto } from "./logica";

// F4, Tarea 13: «Registrar / Retirar una cotización…» salieron de Presupuesto › Precios y viven en Mercado
// (paginas/mercado/Cotizaciones.test.tsx). Aquí queda el enlace que lleva allí, solo para quien puede cotizar.
configure({ asyncUtilTimeout: 5000 });

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const sesion = (acciones: string[]): SesionRespuesta => ({
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones,
  modo_entrega: false,
});

const OBRA = { carpeta: null, obraId: 3, ficha: { estado: "sin_dato" }, recargarFicha: vi.fn() } as ObraAbierta;
const ID = "id-borrador-aaaaaaaaaaaa";
const BORRADOR: BorradorAbierto = {
  id: ID,
  base: { proyecto: "OF-001", version: "002", vigente: "002", lista: "Lista", espacio_de: "002", solo_lectura: false, moneda: "USD" },
  resumen: {
    rev: 0,
    moneda: "USD",
    total: { texto: "2703.86", exacto: "2703.86" },
    cambios: 0,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
  },
  instantanea: { creadas: 0, mensaje: null },
};
const fila = (codigo: string, vigente: boolean) => ({ codigo, fecha: "2026-10-06", motivo: "", origen: "", vigente, descartada: false, cambios: 0 });

const fetchFalso = vi.fn<typeof fetch>();

function montar(acciones: string[]) {
  const valor: Aplicacion = { sesion: sesion(acciones), proyecto: "OF-001", caso: { nombre: "obra", ruta_relativa: "data/obra.db" }, recargarProyectos: vi.fn(), alExpirar: vi.fn() };
  render(
    <ContextoAplicacion.Provider value={valor}>
      <ContextoDeLaObra.Provider value={OBRA}>
        <MemoryRouter>
          <PaginaHoja />
        </MemoryRouter>
      </ContextoDeLaObra.Provider>
    </ContextoAplicacion.Provider>,
  );
}

async function irAPrecios() {
  await userEvent.click(await screen.findByRole("tab", { name: "Precios" }));
  await screen.findByRole("table", { name: "Precios" });
}

describe("Presupuesto › Precios, hacia Mercado", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = new URL(String(ruta), "http://silice.local");
      const metodo = init?.method ?? "GET";
      if (url.pathname === "/v1/hoja/versiones") return json({ proyecto: "OF-001", moneda: "USD", por_omision: "002", versiones: [fila("002", true)] });
      if (url.pathname === "/v1/hoja/borradores" && metodo === "GET") return json({ borradores: [] });
      if (url.pathname === "/v1/hoja/borradores" && metodo === "POST") return json(BORRADOR, 201);
      if (url.pathname === "/v1/hoja/precios") return json(preciosRespuesta());
      if (url.pathname === "/v1/hoja/precios/atipicos") return json(atipicosRespuesta());
      if (url.pathname.includes("/vistas/")) return json(cuerpoDeVista(url.pathname));
      return new Response(null, { status: 204 });
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("con permiso de cotizar: ya no hay «Registrar» ni «Retirar» y sí el enlace a Mercado", async () => {
    montar(["editar_hoja", "leer_proyecto"]);
    await irAPrecios();
    expect(screen.queryByRole("button", { name: "Registrar una cotización…" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Retirar una cotización…" })).toBeNull();
    expect(screen.getByRole("link", { name: "Registrar una cotización en Mercado" })).toHaveAttribute("href", "/obra/empresa/3/mercado");
  });

  test("quien solo revisa no ve el enlace: cotizar exige editar_hoja", async () => {
    montar(["leer_proyecto"]);
    await irAPrecios();
    expect(screen.queryByRole("link", { name: /cotización en Mercado/ })).toBeNull();
  });
});
