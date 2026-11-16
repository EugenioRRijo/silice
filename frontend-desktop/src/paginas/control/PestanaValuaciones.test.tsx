import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Valuaciones } from "./logica";
import { PestanaValuaciones } from "./PestanaValuaciones";

// Datos ficticios (los de Control.test.tsx). Estas pruebas miran lo que la pestaña manda cuando la lista que tiene a la
// vista ya cambió: tras anular, o mientras un archivo todavía se está leyendo.
function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["control_de_obra"],
  modo_entrega: false,
};

const V01 = { id: 7, rotulo: "V-01 (02/11/2026 a 06/11/2026)" };
const V02 = { id: 8, rotulo: "V-02 (09/11/2026 a 13/11/2026)" };

function valuaciones(anulables: Valuaciones["anulables"]): Valuaciones {
  return {
    tiene_linea_base: true,
    filas: [],
    impuestos: { subtotal: "0", iva: "0", total: "0", alicuota: "0.16", fuente_alicuota: "Decreto ficticio" },
    perspectiva: "costo",
    aviso: "",
    anulables,
    corte_por_defecto: "2026-11-13",
    causas: [],
  };
}

// La pestaña vuelve a leer las valuaciones cuando sube su `clave`: aquí sube con cada escritura, como en la página.
function Envoltura() {
  const [clave, setClave] = useState(0);
  return <PestanaValuaciones proyecto="OB-S2" clave={clave} alCambiar={() => setClave((c) => c + 1)} />;
}

describe("Pestaña de valuaciones", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let anulables: Valuaciones["anulables"];
  let informe: (cuerpo: FormData) => Response | Promise<Response>;
  let importar: () => Response | Promise<Response>;

  function montar() {
    render(
      <ContextoAplicacion.Provider
        value={{ sesion: SESION, proyecto: "OB-S2", caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() }}
      >
        <Envoltura />
      </ContextoAplicacion.Provider>,
    );
    return userEvent.setup();
  }

  function anulacionesPedidas(): string[] {
    return fetchFalso.mock.calls.map(([u]) => String(u)).filter((u) => u.endsWith("/anular"));
  }

  beforeEach(() => {
    fijarCsrf("tok");
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    anulables = [V01, V02];
    informe = () => json({ informe: ["sin novedades"] });
    importar = () => json({ importadas: 1 });
    fetchFalso.mockImplementation(async (entrada, init) => {
      const url = String(entrada);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/control/valuaciones?") && metodo === "GET") return json(valuaciones(anulables));
      const anular = /^\/v1\/control\/valuaciones\/(\d+)\/anular$/.exec(url);
      if (anular && metodo === "POST") {
        anulables = anulables.filter((a) => String(a.id) !== anular[1]);
        return json({ anulada: Number(anular[1]) });
      }
      if (url === "/v1/control/importar/informe") return informe(init?.body as FormData);
      if (url === "/v1/control/importar") return importar();
      return json({ detalle: `ruta inesperada ${metodo} ${url}` }, 500);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    fijarCsrf(null);
  });

  // Tras anular V-02 la lista ya no la trae y el selector muestra V-01; el segundo «Anular» mandaba otra vez V-02.
  test("tras anular una valuación, el siguiente «Anular» manda la que muestra el selector", async () => {
    const u = montar();
    const selector = await screen.findByLabelText("Valuación");
    await u.selectOptions(selector, String(V02.id));
    await u.click(screen.getByRole("button", { name: "Anular" }));
    expect(await screen.findByText("Valuación anulada: se conserva y ya no cuenta.")).toBeInTheDocument();
    await waitFor(() => expect(within(screen.getByLabelText("Valuación")).getAllByRole("option")).toHaveLength(1));
    expect(screen.getByLabelText("Valuación")).toHaveValue(String(V01.id));
    await u.click(screen.getByRole("button", { name: "Anular" }));
    await waitFor(() => expect(anulacionesPedidas()).toHaveLength(2));
    expect(anulacionesPedidas()).toEqual([`/v1/control/valuaciones/${V02.id}/anular`, `/v1/control/valuaciones/${V01.id}/anular`]);
  });
});
