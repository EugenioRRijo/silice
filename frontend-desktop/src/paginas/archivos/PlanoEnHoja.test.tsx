import { configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { informeAuditoria, vistaEspacio } from "../hoja/datosDePrueba";
import PaginaHoja from "../hoja/index";
import type { BorradorAbierto, VersionesRespuesta } from "../hoja/logica";
import { ProveedorDeLaHoja } from "../hoja/ProveedorDeLaHoja";
import { importada, respuestaDeFusion } from "./datosDePlano";
import PaginaArchivos from "./index";
import { olvidarImportaciones } from "./useImportacion";

// Rebanada 3e-2, enganche del plano con la Hoja. Desde la Tarea 11 de F4 el plano se importa en Archivos y planos, no en la
// pestaña Espacio: las dos pantallas comparten el borrador (`ProveedorDeLaHoja`), así que lo fusionado allí se ve en el
// Presupuesto: la barra de estado toma el resumen nuevo y las tablas del espacio muestran las filas que entraron (3e-F3).
// Cambió el montaje (las dos pantallas bajo un mismo proveedor); las aserciones son las de antes. Las dos pruebas de la
// pausa de edición del espacio («Fusionar» no se pulsa con una edición en vuelo; las tablas no se editan mientras se
// fusiona) se retiraron: el plano y las tablas del espacio ya no están nunca en la misma pantalla.
configure({ asyncUtilTimeout: 5000 });

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto"],
  modo_entrega: false,
};
const ID = "id-borrador-plano-0001";
const VERSIONES: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "002",
  versiones: [{ codigo: "002", fecha: "2026-10-06", motivo: "edicion", origen: "001", vigente: true, descartada: false, cambios: 0 }],
};
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

const RESUMEN_FUSIONADO = { ...BORRADOR.resumen, rev: 1, cambios: 3, total: { texto: "3000.50", exacto: "3000.50" } };

// Archivos y planos y el Presupuesto bajo el mismo proveedor, como en la obra: el botón cambia de sección.
function DosSecciones() {
  const [seccion, setSeccion] = useState<"archivos" | "presupuesto">("archivos");
  return (
    <ProveedorDeLaHoja>
      <button type="button" onClick={() => setSeccion("presupuesto")}>
        Ir al Presupuesto
      </button>
      {seccion === "archivos" ? <PaginaArchivos /> : <PaginaHoja />}
    </ProveedorDeLaHoja>
  );
}

describe("el plano importado en Archivos y planos entra en la Hoja (3e-2)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  let fusionado = false;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fusionado = false;
    olvidarImportaciones(); // lo último que se leyó de un borrador se recuerda por id: cada prueba parte de cero
    fetchFalso.mockImplementation(async (ruta, init) => {
      const camino = new URL(String(ruta), "http://silice.local").pathname;
      const metodo = init?.method ?? "GET";
      if (camino === "/v1/hoja/versiones") return json(VERSIONES);
      if (camino === "/v1/hoja/importaciones") return json({ importaciones: [] });
      if (camino === "/v1/hoja/borradores" && metodo === "GET") return json({ borradores: [] });
      if (camino === "/v1/hoja/borradores" && metodo === "POST") return json(BORRADOR, 201);
      if (camino === `/v1/hoja/borradores/${ID}` && metodo === "GET") return json({ id: ID, base: BORRADOR.base, resumen: fusionado ? RESUMEN_FUSIONADO : BORRADOR.resumen });
      if (camino === `/v1/hoja/borradores/${ID}/plano` && metodo === "POST") return json(importada());
      if (camino === `/v1/hoja/borradores/${ID}/plano/fusionar`) {
        fusionado = true;
        return json({ ...respuestaDeFusion(1), resumen: RESUMEN_FUSIONADO });
      }
      if (camino.endsWith("/vistas/espacio")) {
        return json(
          fusionado
            ? vistaEspacio({
                filas: { ...vistaEspacio().filas, ambientes: [{ id: "PLN-01", nombre: "Sala del plano", largo: "4" }] },
                total: { texto: "3000.50", exacto: "3000.50" },
              })
            : vistaEspacio(),
        );
      }
      if (camino.endsWith("/vistas/auditoria")) return json(informeAuditoria());
      return new Response(null, { status: 204 });
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const valor = (): Aplicacion => ({
    sesion: SESION,
    proyecto: "OF-001",
    caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
    recargarProyectos: vi.fn(),
    alExpirar,
  });

  test("tras fusionar: el total de la barra de estado es el nuevo y las tablas muestran las filas del plano", async () => {
    const usuario = userEvent.setup();
    render(
      <ContextoAplicacion.Provider value={valor()}>
        <DosSecciones />
      </ContextoAplicacion.Provider>,
    );
    await usuario.click(await screen.findByRole("button", { name: "Subir plano o cómputo" }));
    const dialogo = await screen.findByRole("dialog", { name: "Subir plano o cómputo" });
    await usuario.upload(dialogo.querySelector('input[type="file"]') as HTMLInputElement, new File(["0\nEOF"], "of001.dxf"));
    await usuario.click(within(dialogo).getByRole("button", { name: "Leer plano" }));
    await usuario.click(await within(dialogo).findByRole("button", { name: "Fusionar con el espacio del borrador" }));
    await within(dialogo).findByText(/Se fusionó «of001.dxf» con el borrador de la hoja: 6 ambientes, 6 fuentes y 21 puntos/);
    await waitFor(() => expect(within(dialogo).getByRole("button", { name: "Cerrar" })).toBeEnabled());
    await usuario.click(within(dialogo).getByRole("button", { name: "Cerrar" }));
    await usuario.click(screen.getByRole("button", { name: "Ir al Presupuesto" }));
    const estado = await screen.findByRole("region", { name: "Estado del borrador" });
    expect(await within(estado).findByText(/Total 3\.000,50 USD/)).toBeInTheDocument();
    expect(within(estado).getByText(/3 cambios sin guardar/)).toBeInTheDocument();
    const tabla = await screen.findByRole("table", { name: /Ambientes/ });
    expect(await within(tabla).findByDisplayValue("PLN-01")).toBeInTheDocument();
    expect(within(tabla).queryByDisplayValue("BAN-01")).toBeNull();
    // Un solo borrador para las dos secciones.
    expect(fetchFalso.mock.calls.filter(([r, i]) => String(r) === "/v1/hoja/borradores" && i?.method === "POST")).toHaveLength(1);
  });
});
