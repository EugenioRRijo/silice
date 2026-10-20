import { configure, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import {
  atipicosRespuesta,
  cuerpoDeVista,
  preciosRespuesta,
  trazabilidadRespuesta,
  vistaEquilibrio,
  vistaParametros,
} from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, VersionesRespuesta } from "./logica";

// La primera vista tarda en una máquina cargada (importa Carbon y la tabla): se espera más que el 1 s por omisión.
configure({ asyncUtilTimeout: 5000 });

// El gráfico de Carbon no se dibuja en jsdom: se deja una marca con las filas que recibiría.
vi.mock("../../comun/GraficoCarbon", () => ({
  default: ({ datos }: { datos: unknown[] }) => <div data-testid="grafico" data-filas={datos.length} />,
}));

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

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
const VERSIONES: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "002",
  versiones: [
    { codigo: "001", fecha: "2026-10-05", motivo: "", origen: "", vigente: false, descartada: false, cambios: 0 },
    { codigo: "002", fecha: "2026-10-06", motivo: "edicion", origen: "001", vigente: true, descartada: false, cambios: 1 },
  ],
};

function borrador(version: string | null = "002"): BorradorAbierto {
  return {
    id: ID,
    base: { proyecto: "OF-001", version, vigente: "002", lista: "Lista MaPreX", espacio_de: version, solo_lectura: false, moneda: "USD" },
    resumen: {
      rev: 0,
      moneda: "USD",
      total: { texto: "2703.86", exacto: "2703.860232344044033333333333" },
      cambios: 0,
      pendientes_catalogo: 0,
      hallazgos: [],
      hay_plan: true,
      version_mas_nueva: null,
      guardado_como: null,
    },
    instantanea: { creadas: 0, mensaje: null },
  };
}

type Respuesta = (url: string) => Response | Promise<Response>;
interface Propias {
  vistas?: Partial<Record<"espacio" | "presupuesto" | "equilibrio" | "parametros" | "auditoria", Respuesta>>;
  precios?: Respuesta;
  atipicos?: Respuesta;
  trazabilidad?: Respuesta;
  version?: string | null;
}

describe("Hoja del proyecto: Equilibrio, Parámetros, Auditoría, Precios y Trazabilidad (3b-3)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    localStorage.clear();
    sessionStorage.clear();
  });
  afterEach(() => vi.unstubAllGlobals());

  function servidor(propias: Propias = {}) {
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = String(ruta);
      const metodo = init?.method ?? "GET";
      if (url.startsWith("/v1/hoja/versiones")) return json(VERSIONES);
      if (url === "/v1/hoja/borradores" && metodo === "POST") return json(borrador(propias.version), 201);
      if (url.includes("/vistas/")) {
        const nombre = /\/vistas\/([a-z]+)/.exec(url)![1] as keyof NonNullable<Propias["vistas"]>;
        const propia = propias.vistas?.[nombre];
        return propia ? propia(url) : json(cuerpoDeVista(url));
      }
      if (url.startsWith("/v1/hoja/precios/atipicos")) return (propias.atipicos ?? (() => json(atipicosRespuesta())))(url);
      if (url.startsWith("/v1/hoja/precios")) return (propias.precios ?? (() => json(preciosRespuesta())))(url);
      if (url.startsWith("/v1/hoja/trazabilidad")) return (propias.trazabilidad ?? (() => json(trazabilidadRespuesta())))(url);
      return new Response(null, { status: 204 });
    });
  }

  function montar() {
    const valor: Aplicacion = {
      sesion: SESION,
      proyecto: "OF-001",
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
    return render(
      <ContextoAplicacion.Provider value={valor}>
        <PaginaHoja />
      </ContextoAplicacion.Provider>,
    );
  }

  async function irA(pestana: string) {
    await screen.findByRole("region", { name: "Estado del borrador" });
    await userEvent.click(screen.getByRole("tab", { name: pestana }));
  }

  // --- Punto de equilibrio ------------------------------------------------------------------------

  test("3b-F9: las cuatro métricas, el punto, su porcentaje y la frase del caso (cifras de OF-001)", async () => {
    servidor();
    montar();
    await irA("Punto de equilibrio");
    const rotulo = await screen.findByText("Ventas (contrato)");
    const dl = rotulo.closest("dl")!;
    expect(within(dl).getByText("Ventas (contrato)").nextElementSibling).toHaveTextContent("2.703,86 USD");
    expect(within(dl).getByText("Costo variable").nextElementSibling).toHaveTextContent("2.137,44 USD");
    expect(within(dl).getByText("Costo fijo").nextElementSibling).toHaveTextContent("427,49 USD");
    expect(within(dl).getByText("Utilidad").nextElementSibling).toHaveTextContent("138,93 USD");
    expect(within(dl).getByText("Punto de equilibrio").nextElementSibling).toHaveTextContent("1.530,49 USD");
    expect(within(dl).getByText("Como % de las ventas").nextElementSibling).toHaveTextContent("56,60 %");
    expect(within(dl).getByText("Se alcanza en").nextElementSibling).toHaveTextContent("Día 23");
    // El exacto va en el title y en un texto accesible; nada se redondea en la interfaz.
    expect(within(dl).getByTitle("1530.4912345")).toBeInTheDocument();
    expect(within(dl).getByText(/Valor exacto 1530.4912345/)).toBeInTheDocument();
    expect(screen.getByText("Se alcanza en Dia 23, al 50 % de ese periodo.")).toBeInTheDocument();
  });

  test("3b-F9: sin punto de equilibrio no se muestra «Punto de equilibrio» y sí la frase que lo explica", async () => {
    const mensaje = "El presupuesto no tiene ventas: el punto de equilibrio no aplica.";
    servidor({
      vistas: {
        equilibrio: () =>
          json(vistaEquilibrio({ estado: "sin_ventas", punto: null, porcentaje: null, periodo: null, fraccion_periodo: null, mensaje })),
      },
    });
    montar();
    await irA("Punto de equilibrio");
    expect(await screen.findByText(mensaje)).toBeInTheDocument();
    expect(screen.getByText("Ventas (contrato)")).toBeInTheDocument();
    expect(screen.queryByText("Punto de equilibrio", { selector: "dt" })).toBeNull();
    expect(screen.queryByText("Como % de las ventas")).toBeNull();
    expect(screen.queryByText("Se alcanza en")).toBeNull();
  });

  test("3b-F9: el punto sin período (sin curva) muestra el punto y la frase, sin «Se alcanza en»", async () => {
    const mensaje = "Sin curva de inversión: el punto de equilibrio no se ubica en el plan.";
    servidor({ vistas: { equilibrio: () => json(vistaEquilibrio({ periodo: null, fraccion_periodo: null, mensaje })) } });
    montar();
    await irA("Punto de equilibrio");
    expect(await screen.findByText(mensaje)).toBeInTheDocument();
    expect(screen.getByText("Punto de equilibrio", { selector: "dt" })).toBeInTheDocument();
    expect(screen.queryByText("Se alcanza en")).toBeNull();
  });

  test("3b-F9: un monto de treinta cifras no pierde ninguna", async () => {
    const largo = "1234567890123456789012345.123456789012";
    servidor({ vistas: { equilibrio: () => json(vistaEquilibrio({ venta: { texto: largo, exacto: largo } })) } });
    montar();
    await irA("Punto de equilibrio");
    expect(await screen.findByText(/1\.234\.567\.890\.123\.456\.789\.012\.345,123456789012 USD/)).toBeInTheDocument();
  });

  // --- Parámetros ---------------------------------------------------------------------------------

  test("Parámetros: los cuatro parámetros de costo en lectura, con es-VE y su valor escrito en el title", async () => {
    servidor();
    montar();
    await irA("Parámetros");
    const lista = (await screen.findByText(/^FCAS/)).closest("dl")!;
    const fila = (rotulo: RegExp) => within(lista).getByText(rotulo).nextElementSibling!;
    expect(fila(/^FCAS/)).toHaveTextContent("6,00");
    expect(fila(/^FCAS/).querySelector('[title="6.00"]')).not.toBeNull();
    expect(fila(/^Bono de alimentación/)).toHaveTextContent("3,5");
    expect(fila(/^Administración/)).toHaveTextContent("0,20");
    expect(fila(/^Utilidad/)).toHaveTextContent("0,10");
    // En esta entrega solo se leen: editarlos es de la rebanada 3c.
    expect(screen.queryAllByRole("textbox")).toEqual([]);
  });

  test("Parámetros: la moneda del proyecto y el total del presupuesto", async () => {
    servidor();
    montar();
    await irA("Parámetros");
    expect(await screen.findByText("Moneda del proyecto: USD")).toBeInTheDocument();
    expect(screen.getByTitle("2703.860232344044")).toHaveTextContent("2.703,86 USD");
  });

  test("Parámetros: sin moneda del proyecto no se inventa una", async () => {
    servidor({ vistas: { parametros: () => json(vistaParametros({ moneda_proyecto: null })) } });
    montar();
    await irA("Parámetros");
    await screen.findByText(/^FCAS/);
    expect(screen.queryByText(/Moneda del proyecto/)).toBeNull();
  });
});
