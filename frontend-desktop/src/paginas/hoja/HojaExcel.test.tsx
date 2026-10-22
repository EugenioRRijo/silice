import { configure, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import { informeAuditoria, vistaEspacio } from "./datosDePrueba";
import PaginaHoja from "./index";

// 3e-F4 en la página: el botón aparece cuando el borrador está abierto, descarga el del id que abrió el servidor y la
// descarga no cambia el borrador (ninguna otra petición que no sea el GET del libro).
configure({ asyncUtilTimeout: 5000 });
const json = (c: unknown, e = 200) =>
  new Response(JSON.stringify(c), { status: e, headers: { "Content-Type": "application/json" } });
const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja"],
  modo_entrega: false,
};
const ID = "id-borrador-aaaaaaaaaaaa";
const m = (t: string) => ({ texto: t, exacto: t });

describe("Hoja del proyecto: Descargar Excel (3e-1)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    URL.createObjectURL = vi.fn(() => "blob:falso");
    URL.revokeObjectURL = vi.fn();
    fetchFalso.mockImplementation(async (ruta, init) => {
      const camino = new URL(String(ruta), "http://silice.local").pathname;
      const metodo = init?.method ?? "GET";
      if (camino === "/v1/hoja/versiones") {
        return json({
          proyecto: "OF-001",
          moneda: "USD",
          por_omision: "001",
          versiones: [{ codigo: "001", fecha: "2026-10-05", motivo: "", origen: "", vigente: true, descartada: false, cambios: 0 }],
        });
      }
      if (camino === "/v1/hoja/borradores" && metodo === "GET") return json({ borradores: [] });
      if (camino === "/v1/hoja/borradores" && metodo === "POST") {
        return json(
          {
            id: ID,
            base: { proyecto: "OF-001", version: "001", vigente: "001", lista: "L", espacio_de: "001", solo_lectura: false, moneda: "USD" },
            resumen: { rev: 0, moneda: "USD", total: m("2703.86"), cambios: 0, pendientes_catalogo: 0, hallazgos: [], hay_plan: true, version_mas_nueva: null, guardado_como: null },
            instantanea: { creadas: 0, mensaje: null },
          },
          201,
        );
      }
      if (camino.endsWith("/excel")) {
        return new Response(new Uint8Array([80, 75]), { status: 200, headers: { "Content-Disposition": 'attachment; filename="hoja_001.xlsx"' } });
      }
      if (camino.endsWith("/vistas/espacio")) return json(vistaEspacio());
      if (camino.endsWith("/vistas/auditoria")) return json(informeAuditoria());
      return new Response(null, { status: 204 });
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  test("el botón aparece con el borrador abierto, pide el libro de ese borrador y no toca nada más", async () => {
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    render(
      <ContextoAplicacion.Provider
        value={{ sesion: SESION, proyecto: "OF-001", caso: { nombre: "o", ruta_relativa: "data/o.db" }, recargarProyectos: vi.fn(), alExpirar: vi.fn() }}
      >
        <PaginaHoja />
      </ContextoAplicacion.Provider>,
    );
    expect(screen.queryByRole("button", { name: "Descargar Excel" })).toBeNull();
    const boton = await screen.findByRole("button", { name: "Descargar Excel" });
    const antes = fetchFalso.mock.calls.length;
    await userEvent.click(boton);
    await waitFor(() => expect(fetchFalso.mock.calls.length).toBeGreaterThan(antes));
    const nuevas = fetchFalso.mock.calls.slice(antes).map(([r, i]) => `${i?.method ?? "GET"} ${String(r)}`);
    expect(nuevas).toEqual([`GET /v1/hoja/borradores/${ID}/excel`]);
  });
});
