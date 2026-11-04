import { configure, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import { resultadosDe } from "../../marco/busqueda";
import { ofertaDe } from "../../marco/oferta";
import { ACCIONES, json, ligeras, montarMarco, servidorFalso, sesionDe } from "../../shell/obras/datosDePrueba";
import type { Rol } from "../../shell/obras/datosDePrueba";
import { paginaPorId, usable } from "../../shell/rutas";
import { cancelarSalida } from "../../shell/salida";
import { olvidarFormularios } from "../../shell/sucio";
import { preciosRespuesta } from "../hoja/datosDePrueba";
import type { PreciosRespuesta, VersionesRespuesta } from "../hoja/logica";
import PaginaMercado from "./index";

// Ronda 2 de la Tarea 13 del plan F4. Antes del traslado, la pantalla suelta del histórico pedía `leer_proyecto` y quien
// revisa la veía; ahora vive en Mercado. Estas pruebas pasan por el PERMISO REAL (las acciones de cada rol escritas a mano
// desde seguridad/permisos.py, `ACCIONES` de datosDePrueba; el registro de `shell/rutas.ts`; la oferta del árbol y del
// buscador; el marco entero): quien revisa llega a Mercado y ve lo que lee (histórico y cotizaciones), sin nada que escriba.
// Obra ficticia 7 («Casa Demo») de la carpeta de la empresa; versión vigente 002 con una cotización ficticia en MAT-002.
configure({ asyncUtilTimeout: 5000 });

const VERSIONES: VersionesRespuesta = {
  proyecto: "7",
  moneda: "USD",
  por_omision: "002",
  versiones: [{ codigo: "002", fecha: "2026-10-06", motivo: "", origen: "", vigente: true, descartada: false, cambios: 0 }],
};

function precios(): PreciosRespuesta {
  const base = preciosRespuesta();
  return {
    ...base,
    filas: base.filas.map((f) => (f["codigo"] === "MAT-002" ? { ...f, cotizacion: "COT-17 · Ferretería Demo", moneda_original: "Bs" } : f)),
  };
}

const CAMBIO = { insumo: "Cemento gris ficticio", precio_anterior: "16.0000", precio_nuevo: "18.0000", variacion: "0.1250", fecha: "2026-02-01" };

let servidor: ReturnType<typeof servidorFalso>;

beforeEach(() => {
  servidor = servidorFalso(undefined, (metodo, ruta) => {
    const camino = new URL(ruta, "http://silice.local").pathname;
    if (camino === "/v1/hoja/versiones" && metodo === "GET") return json(VERSIONES);
    if (camino === "/v1/hoja/precios") return json(precios());
    if (camino === "/cambios-precio") return json([CAMBIO]);
    if (camino === "/insumos") return json([]);
    return undefined;
  });
  vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
  fijarCsrf("tok");
});
afterEach(() => {
  cancelarSalida();
  olvidarFormularios();
  vi.unstubAllGlobals();
  fijarCsrf(null);
});

const montar = (rol: Rol) => {
  montarMarco(sesionDe(rol), "/obra/empresa/7/mercado", ligeras({ mercado: PaginaMercado }));
  return userEvent.setup();
};
const pestanas = () => screen.getAllByRole("tab").map((t) => t.textContent);

describe("Mercado para quien revisa (ronda 2 de la Tarea 13)", () => {
  test("con las acciones de quien revisa, Mercado es usable y se ofrece en el árbol y en el buscador (Ctrl+K)", () => {
    const oferta = ofertaDe(ACCIONES.rita, false);
    expect(usable(paginaPorId("mercado")!, ACCIONES.rita, false)).toBe(true);
    expect(oferta.secciones.map((s) => s.id)).toContain("mercado");
    const obra = { carpeta: null, carpeta_titulo: "Carpeta de la empresa", obra_id: 7, obra: "Casa Demo", version_codigo: null };
    expect(resultadosDe("casa mercado", [obra], oferta).map((r) => r.texto)).toContain("Casa Demo › Mercado");
  });

  test("quien revisa abre Mercado desde la barra de la obra y solo ve las pestañas que leen", async () => {
    montar("rita");
    const barra = await screen.findByRole("navigation", { name: "Secciones de la obra" });
    expect(await within(barra).findByRole("link", { name: "Mercado" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 1, name: "Estudio de mercado" })).toBeInTheDocument();
    expect(pestanas()).toEqual(["Histórico de precios", "Cotizaciones de la obra"]);
    // «Lo que compramos» y «Lo que cobramos» anotan y usan precios (y su estudio exige `editar_hoja`): no se pintan.
    expect(screen.queryByRole("combobox", { name: "Partida" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Ver estos días" })).toBeNull();
  });

  test("quien revisa lee el histórico de precios", async () => {
    const u = montar("rita");
    await u.click(await screen.findByRole("tab", { name: "Histórico de precios" }));
    expect(await screen.findByRole("heading", { level: 2, name: "Histórico de cambios de precio" })).toBeInTheDocument();
    const tabla = await screen.findByRole("table", { name: "Cambios de precio" });
    expect(await within(tabla).findByText("12,50 %")).toBeInTheDocument();
  });

  test("quien revisa ve las cotizaciones de la obra sin «Registrar» ni «Retirar»", async () => {
    const u = montar("rita");
    await u.click(await screen.findByRole("tab", { name: "Cotizaciones de la obra" }));
    const tabla = await screen.findByRole("table", { name: "Cotizaciones de la obra" });
    await waitFor(() => expect(within(tabla).getByText("COT-17 · Ferretería Demo")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /Registrar una cotización/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /Retirar una cotización/ })).toBeNull();
    expect(servidor.llamadas.filter((l) => l.metodo !== "GET" && l.ruta.startsWith("/v1/hoja/versiones/"))).toEqual([]);
  });

  test("con las acciones de quien arma, todo sigue como en la ronda 1: cuatro pestañas y las dos operaciones", async () => {
    const u = montar("ana");
    expect(await screen.findByRole("heading", { level: 1, name: "Estudio de mercado" })).toBeInTheDocument();
    expect(pestanas()).toEqual(["Lo que compramos", "Lo que cobramos", "Histórico de precios", "Cotizaciones de la obra"]);
    expect(screen.getByRole("combobox", { name: "Insumo" })).toBeInTheDocument();
    await u.click(screen.getByRole("tab", { name: "Histórico de precios" }));
    expect(await screen.findByRole("heading", { level: 2, name: "Histórico de cambios de precio" })).toBeInTheDocument();
    await u.click(screen.getByRole("tab", { name: "Cotizaciones de la obra" }));
    expect(await screen.findByRole("button", { name: /Registrar una cotización/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Retirar una cotización/ })).toBeInTheDocument();
  });
});
