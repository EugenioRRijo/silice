import { configure, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { vistaPresupuesto } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, Resumen, VersionesRespuesta, VistaPresupuesto } from "./logica";

// Tarea 5b del plan F4 (decisión de Eugenio, 31/10/2026, plan vial T18): debajo de «Total del presupuesto» se leen el
// subtotal, el IVA y el total con IVA que manda el servidor; la interfaz no calcula. Obra ficticia OF-001; las cifras
// esperadas están escritas a mano: 1.000,00 -> 160,00 -> 1.160,00 y un medio céntimo que sube (0,01).
configure({ asyncUtilTimeout: 5000 });

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const EDITA: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto"],
  modo_entrega: false,
};
const REVISA: SesionRespuesta = { ...EDITA, login: "rita", nombre: "Rita Gómez", roles: ["revisa"], acciones: ["leer_proyecto"] };

const ID = "id-borrador-aaaaaaaaaaaa";
const VERSIONES: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "001",
  versiones: [{ codigo: "001", fecha: "2026-10-05", motivo: "", origen: "", vigente: true, descartada: false, cambios: 0 }],
};
const m = (texto: string, exacto = texto) => ({ texto, exacto });
const FUENTE =
  "Ley del IVA, alícuota general: Decreto 3.584, G.O. 6.395 Ext., 17-08-2018 (16 %) — a cotejar con la Gaceta vigente";

function resumen(): Resumen {
  return {
    rev: 0,
    moneda: "USD",
    total: m("1000.00"),
    cambios: 0,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
    espacio_vacio: true,
  };
}

const BORRADOR: BorradorAbierto = {
  id: ID,
  base: { proyecto: "OF-001", version: "001", vigente: "001", lista: "Lista", espacio_de: "001", solo_lectura: false, moneda: "USD" },
  resumen: resumen(),
  instantanea: { creadas: 0, mensaje: null },
};

// La vista que manda el servidor, con `impuestos` ya calculado (no se calcula en la interfaz).
function presupuesto(impuestos: { subtotal: string; iva: string; total: string }, conPartidas = true): VistaPresupuesto {
  const [fila] = vistaPresupuesto().filas;
  return {
    ...vistaPresupuesto(),
    filas: conPartidas ? [{ ...fila!, clave: "E-01|version", partida: "E-01", descripcion: "Excavación en tierra", unidad: "m3" }] : [],
    total: m(impuestos.subtotal),
    impuestos: { ...impuestos, alicuota: "0.16", fuente_alicuota: FUENTE },
  } as VistaPresupuesto;
}

describe("Presupuesto: subtotal, IVA y total con IVA (Tarea 5b)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let vista: VistaPresupuesto;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    localStorage.clear();
    sessionStorage.clear();
    vista = presupuesto({ subtotal: "1000.00", iva: "160.00", total: "1160.00" });
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = new URL(String(ruta), "http://silice.local");
      const metodo = init?.method ?? "GET";
      const camino = decodeURIComponent(url.pathname);
      if (camino === "/v1/hoja/versiones") return json(VERSIONES);
      if (camino === "/v1/hoja/borradores" && metodo === "POST") return json(BORRADOR, 201);
      if (camino === "/v1/hoja/borradores" && metodo === "GET") return json([]);
      if (camino.endsWith("/vistas/presupuesto")) return json(vista);
      return new Response(null, { status: 204 });
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  function montar(sesion: SesionRespuesta = EDITA) {
    const valor: Aplicacion = {
      sesion,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar: vi.fn(),
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <PaginaHoja />
      </ContextoAplicacion.Provider>,
    );
  }

  async function regionDelIva(sesion: SesionRespuesta = EDITA): Promise<HTMLElement> {
    montar(sesion);
    await screen.findByText("Excavación en tierra");
    const region = screen.queryByRole("region", { name: "IVA del presupuesto" });
    expect(region, "debajo del total hay la región «IVA del presupuesto»").not.toBeNull();
    return region!;
  }

  test("quien arma lee el subtotal, el IVA (16 %) y el total con IVA con coma decimal y la moneda de la obra", async () => {
    const region = await regionDelIva();
    expect(within(region).getByText("Subtotal").closest("p")).toHaveTextContent("Subtotal 1.000,00 USD");
    expect(within(region).getByText("IVA (16 %)").closest("p")).toHaveTextContent("IVA (16 %) 160,00 USD");
    expect(within(region).getByText("Total con IVA").closest("p")).toHaveTextContent("Total con IVA 1.160,00 USD");
    // El total del presupuesto sigue siendo el costo sin IVA.
    expect(screen.getByText("Total del presupuesto").closest("p")).toHaveTextContent("Total del presupuesto 1.000,00 USD");
  });

  test("el medio céntimo que sube llega tal como lo manda el servidor", async () => {
    vista = presupuesto({ subtotal: "0.03", iva: "0.01", total: "0.04" });
    const region = await regionDelIva();
    expect(within(region).getByText("IVA (16 %)").closest("p")).toHaveTextContent("IVA (16 %) 0,01 USD");
    expect(within(region).getByText("Total con IVA").closest("p")).toHaveTextContent("Total con IVA 0,04 USD");
  });

  test("la fuente de la alícuota está en el «¿Qué es esto?» de la pestaña, plegada hasta pulsarlo", async () => {
    await regionDelIva();
    expect(screen.queryByText(new RegExp("a cotejar con la Gaceta vigente"))).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "¿Qué es esto?" }));
    expect(screen.getByRole("region", { name: "Partidas" })).toHaveTextContent(`Alícuota: 16 %. Fuente: ${FUENTE}.`);
  });

  test("quien revisa también lo ve", async () => {
    const region = await regionDelIva(REVISA);
    expect(within(region).getByText("Total con IVA").closest("p")).toHaveTextContent("Total con IVA 1.160,00 USD");
  });

  test("sin partidas no se pinta", async () => {
    vista = presupuesto({ subtotal: "0.00", iva: "0.00", total: "0.00" }, false);
    montar();
    await screen.findByText(/Total del presupuesto|Todavía no hay/);
    expect(screen.queryByRole("region", { name: "IVA del presupuesto" })).toBeNull();
    expect(screen.queryByText("Total con IVA")).toBeNull();
  });
});
