import { configure, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { PendienteDeObra } from "../../api/tipos";
import { ACCIONES, json, ligeras, montarMarco, servidorFalso, sesionDe } from "../../shell/obras/datosDePrueba";
import type { Rol } from "../../shell/obras/datosDePrueba";
import { paginaPorId, usable } from "../../shell/rutas";
import { cancelarSalida } from "../../shell/salida";
import { olvidarFormularios } from "../../shell/sucio";
import PaginaAprobar from "./index";

// Tanda 2 del pulido F5, Tarea 6. El pendiente «Entregar» (una versión aprobada y sin entregar) lleva a Aprobaciones de su
// obra, que no tenía cómo entregar: «Entregar paquete» solo se abría con Ctrl+K. Ahora Aprobaciones lo ofrece a quien puede
// usar esa pantalla (`entregar_paquete`). Estas pruebas pasan por el PERMISO REAL (las acciones de cada rol de
// `datosDePrueba`, escritas a mano desde seguridad/permisos.py; el registro de `shell/rutas.ts`; el marco entero), como
// `mercado/QuienRevisa.test.tsx`. Obra ficticia 7 («Casa Demo») de la carpeta de la empresa; versión CASA-002 aprobada.
configure({ asyncUtilTimeout: 5000 });

const ENTREGAR: PendienteDeObra = {
  carpeta: null,
  obra_id: 7,
  obra: "Casa Demo",
  grupo: "aprobar",
  urgencia: "bloquea",
  texto: "CASA-002 aprobada y sin entregar",
  accion: { texto: "Entregar", pagina: "entregar" },
};

beforeEach(() => {
  const servidor = servidorFalso(undefined, (metodo, ruta) => {
    const camino = new URL(ruta, "http://silice.local").pathname;
    if (camino === "/v1/obras/pendientes/todas") return json({ pendientes: [ENTREGAR], carpetas_omitidas: 0 });
    if (camino === "/v1/aprobaciones/pendientes" && metodo === "GET") return json([]);
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

const montar = (rol: Rol, ruta: string) => {
  montarMarco(sesionDe(rol), ruta, ligeras({ aprobar: PaginaAprobar }));
  return userEvent.setup();
};

describe("entregar desde Aprobaciones (tanda 2 del pulido F5, Tarea 6)", () => {
  test("con las acciones de cada rol, la pantalla «Entregar paquete» es de quien arma y no de quien revisa", () => {
    const entregar = paginaPorId("entregar")!;
    expect(usable(entregar, ACCIONES.ana, false)).toBe(true);
    expect(usable(entregar, ACCIONES.rita, false)).toBe(false);
  });

  test("quien arma va del pendiente «Entregar» a Aprobaciones de la obra y de ahí a «Entregar paquete»", async () => {
    const u = montar("ana", "/pendientes");
    const detalle = await screen.findByRole("region", { name: "Detalle del pendiente" });
    await u.click(within(detalle).getByRole("button", { name: "Entregar" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Aprobar una versión" })).toBeInTheDocument();

    await u.click(await screen.findByRole("link", { name: "Entregar paquete" }));

    expect(await screen.findByRole("heading", { level: 1, name: "Entregar paquete" })).toBeInTheDocument();
  });

  test("quien revisa ve Aprobaciones de la obra sin «Entregar paquete»", async () => {
    montar("rita", "/obra/empresa/7/aprobaciones");
    expect(await screen.findByRole("heading", { level: 1, name: "Aprobar una versión" })).toBeInTheDocument();
    expect(await screen.findByText("No hay versiones esperando dictamen.")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Entregar paquete" })).toBeNull();
  });
});
