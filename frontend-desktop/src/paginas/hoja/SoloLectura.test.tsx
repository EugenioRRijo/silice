import { configure, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ofertaDe } from "../../marco/oferta";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { paginaPorId, usable } from "../../shell/rutas";
import { cuerpoDeVista, preciosRespuesta, trazabilidadRespuesta, vistaPresupuesto } from "./datosDePrueba";
import PaginaHoja from "./index";
import { PESTANAS } from "./logica";
import type { BorradorAbierto, VersionesRespuesta } from "./logica";
import { puedeEditarLaHoja } from "./puedeEditar";

// F4, Tarea 2b (Eugenio, 2026-10-31): quien revisa ve Presupuesto, Archivos y planos y Versiones en solo lectura. Sin
// permiso de edición no se pinta ningún control que escribe (no se deja deshabilitado): ni botones de edición ni campos.

configure({ asyncUtilTimeout: 5000 });

vi.mock("../../comun/GraficoCarbon", () => ({
  default: ({ datos }: { datos: unknown[] }) => <div data-testid="grafico" data-filas={datos.length} />,
}));

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

// Las acciones de «revisa», escritas a mano (seguridad/permisos.py, S3 §5.1).
const ACCIONES_REVISA = ["leer_proyecto", "aprobar_version", "revisar_paquete", "ver_riesgo"];
const ACCIONES_ARMA = ["editar_hoja", "leer_proyecto", "aprobar_version", "convertir_y_reajustar"];

function sesion(acciones: string[]): SesionRespuesta {
  return {
    login: "rita",
    nombre: "Rita Gómez",
    roles: acciones.includes("editar_hoja") ? ["arma"] : ["revisa"],
    csrf: "tok",
    debe_cambiar_clave: false,
    acciones,
    modo_entrega: false,
  };
}

const ID = "id-borrador-rita-aaaaaaaa";
const VERSIONES: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "002",
  versiones: [
    { codigo: "001", fecha: "2026-10-05", motivo: "", origen: "", vigente: false, descartada: false, cambios: 0 },
    { codigo: "002", fecha: "2026-10-06", motivo: "edicion", origen: "001", vigente: true, descartada: false, cambios: 1 },
  ],
};

function borrador(soloLectura = false): BorradorAbierto {
  return {
    id: ID,
    base: { proyecto: "OF-001", version: "002", vigente: "002", lista: "Lista MaPreX", espacio_de: "002", solo_lectura: soloLectura, moneda: "USD" },
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
}

// Un renglón propio de la versión (se puede quitar) con una cantidad escrita a mano y un hallazgo: con permiso,
// «Quitar», «Volver a la calculada» y la cantidad editable; sin él, solo el texto.
const PRESUPUESTO = vistaPresupuesto({
  filas: [
    ...vistaPresupuesto().filas,
    {
      clave: "OC-EXC",
      partida: "OC-EXC",
      descripcion: "Excavación a mano",
      unidad: "m3",
      cantidad: "1.234,5",
      cantidad_calculada: "1.000",
      escrita: true,
      pu: { texto: "12.50", exacto: "12.5" },
      total: { texto: "15431.25", exacto: "15431.25" },
      estado: { severidad: "ADVERTENCIA", texto: "Cantidad escrita a mano" },
      quitable: true,
      nota: "medido en sitio",
      calculo: null,
    },
  ],
});

// La versión 002 está guardada y sin enviar: se puede enviar (con permiso).
const APROBACIONES = {
  rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." },
  fases: "",
  versiones: { "002": { estado: "guardada", por: null, el: null, notas: "", armo: false } },
  eventos: [],
  ultima_aprobada: null,
};

const fetchFalso = vi.fn<typeof fetch>();

function servidor(soloLectura = false) {
  fetchFalso.mockImplementation(async (ruta, init) => {
    const url = String(ruta);
    const metodo = init?.method ?? "GET";
    if (url.startsWith("/v1/hoja/versiones")) return json(VERSIONES);
    if (url === "/v1/hoja/borradores" && metodo === "GET") return json({ borradores: [] });
    if (url === "/v1/hoja/borradores" && metodo === "POST") return json(borrador(soloLectura), 201);
    if (url.includes("/vistas/presupuesto")) return json(PRESUPUESTO);
    if (url.includes("/vistas/")) return json(cuerpoDeVista(url));
    if (url.startsWith("/v1/hoja/precios/atipicos")) return json({ disponible: false, mensaje: "", variaciones: [] });
    if (url.startsWith("/v1/hoja/precios")) return json(preciosRespuesta());
    if (url.startsWith("/v1/hoja/trazabilidad")) return json(trazabilidadRespuesta());
    if (url.startsWith("/v1/hoja/cadena")) return json({ integra: true, mensaje: "La cadena está íntegra.", declaracion: null });
    if (url.startsWith("/v1/aprobaciones")) return json(APROBACIONES);
    if (url.startsWith("/v1/mercado/objetivos")) return json({ objetivos: [] });
    if (metodo === "DELETE") return new Response(null, { status: 204 });
    return json({ detalle: "ruta inesperada" }, 500);
  });
}

function montar(acciones: string[]) {
  const valor: Aplicacion = {
    sesion: sesion(acciones),
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

// Los controles que escriben, uno por uno (por el comienzo de su nombre accesible: «Quitar fila 2 de Ambientes»,
// «Volver a la calculada, Presupuesto fila 3»…).
const QUE_ESCRIBEN = [
  "Agregar partida",
  "Quitar",
  "Volver a la calculada",
  "Guardar versión…",
  "Guardar primera versión…",
  "Descartar cambios",
  "Agregar línea",
  "Cambiar el insumo de una línea",
  "Usar este insumo",
  "Plan desde los rendimientos",
  "Crear plan secuencial",
  "Agregar fila",
  "Quitar fila",
  "Convertir la moneda…",
  "Registrar una cotización…",
  "Retirar una cotización…",
  "Restaurar una versión…",
  "Enviar a aprobación…",
  "Importar plano (DXF o IFC)",
];

function botonesQueEscriben(): string[] {
  const nombres = screen.queryAllByRole("button").map((b) => b.getAttribute("aria-label") ?? b.textContent ?? "");
  return nombres.filter((n) => QUE_ESCRIBEN.some((q) => n.trim().startsWith(q)));
}

// Los campos que se pueden escribir: los de búsqueda llevan role="searchbox" y no cuentan.
function camposQueEscriben(): HTMLElement[] {
  return [...screen.queryAllByRole("textbox"), ...screen.queryAllByRole("spinbutton")].filter(
    (c) => !c.hasAttribute("readonly"),
  );
}

// Lo que cada pestaña muestra cuando ya cargó (para no mirar antes de tiempo).
const CARGADA: Record<(typeof PESTANAS)[number], string> = {
  "Espacio y metrajes": "Cantidades derivadas",
  APU: "Cierre de partida",
  Presupuesto: "Total del presupuesto",
  "Plan y curva": "Curva de inversión",
  "Punto de equilibrio": "Punto de equilibrio",
  Precios: "Evaluada al",
  Parámetros: "Moneda del proyecto",
  Auditoría: "El informe se genera siempre",
  Trazabilidad: "Versiones del proyecto",
};

async function irA(pestana: (typeof PESTANAS)[number]) {
  await userEvent.click(screen.getByRole("tab", { name: pestana }));
  const panel = screen.getByRole("tabpanel");
  await within(panel).findAllByText(new RegExp(CARGADA[pestana]));
}

beforeEach(() => {
  vi.stubGlobal("fetch", fetchFalso);
  fetchFalso.mockReset();
  localStorage.clear();
  sessionStorage.clear();
});
afterEach(() => vi.unstubAllGlobals());

describe("puedeEditarLaHoja: una sola regla para los controles que escriben", () => {
  test("quien arma, con una base normal, edita", () => {
    expect(puedeEditarLaHoja(ACCIONES_ARMA, { solo_lectura: false })).toBe(true);
  });
  test("quien revisa no edita", () => {
    expect(puedeEditarLaHoja(ACCIONES_REVISA, { solo_lectura: false })).toBe(false);
    expect(puedeEditarLaHoja(ACCIONES_REVISA, null)).toBe(false);
  });
  test("quien arma, con un borrador de solo lectura, no edita", () => {
    expect(puedeEditarLaHoja(ACCIONES_ARMA, { solo_lectura: true })).toBe(false);
  });
});

describe("Quien revisa ve el Presupuesto en solo lectura", () => {
  test("el árbol de la obra le ofrece «Presupuesto»", () => {
    expect(usable(paginaPorId("hoja")!, ACCIONES_REVISA, false)).toBe(true);
    expect(ofertaDe(ACCIONES_REVISA, false).secciones.map((s) => s.titulo)).toContain("Presupuesto");
  });

  test("la nota de solo lectura y la tabla con sus cifras en es-VE", async () => {
    servidor();
    montar(ACCIONES_REVISA);
    expect(await screen.findByRole("note")).toHaveTextContent("Está viendo este presupuesto en solo lectura.");
    await irA("Presupuesto");
    const tabla = screen.getByRole("table", { name: "Presupuesto" });
    expect(within(tabla).getByText("1.234,5")).toBeInTheDocument();
    expect(within(tabla).getByText("15.431,25")).toBeInTheDocument();
    expect(screen.getByText(/Total del presupuesto/)).toHaveTextContent("2.703,86");
  });

  test("en ninguna pestaña hay un control que escriba", async () => {
    servidor();
    montar(ACCIONES_REVISA);
    await screen.findByRole("region", { name: "Estado del borrador" });
    for (const pestana of PESTANAS) {
      await irA(pestana);
      expect({ pestana, botones: botonesQueEscriben() }).toEqual({ pestana, botones: [] });
      expect({ pestana, campos: camposQueEscriben().map((c) => c.id) }).toEqual({ pestana, campos: [] });
      expect(screen.queryByRole("grid")).toBeNull();
    }
    // La aprobación se ve, pero no se envía.
    expect(screen.queryByRole("button", { name: /Enviar a aprobación/ })).toBeNull();
  });

  test("sí están «Descargar Excel», «Ver en Auditoría» y la búsqueda de partida del APU", async () => {
    servidor();
    montar(ACCIONES_REVISA);
    expect(await screen.findByRole("button", { name: "Descargar Excel" })).toBeInTheDocument();
    await irA("Presupuesto");
    expect(screen.getAllByRole("button", { name: /^Ver en Auditoría/ }).length).toBeGreaterThan(0);
    await irA("APU");
    expect(screen.getByRole("searchbox", { name: "Buscar partida" })).toBeInTheDocument();
  });

  test("no pide los objetivos de mercado (son de quien arma)", async () => {
    servidor();
    montar(ACCIONES_REVISA);
    await screen.findByRole("region", { name: "Estado del borrador" });
    await irA("Presupuesto");
    expect(fetchFalso.mock.calls.map(([r]) => String(r)).filter((r) => r.startsWith("/v1/mercado"))).toEqual([]);
  });
});

describe("Quien arma conserva sus controles", () => {
  test("con permiso y base normal: sin nota y con los controles de cada pestaña", async () => {
    servidor();
    montar(ACCIONES_ARMA);
    await screen.findByRole("region", { name: "Estado del borrador" });
    expect(screen.queryByRole("note")).toBeNull();
    await irA("Espacio y metrajes");
    expect(screen.getByRole("button", { name: "Importar plano (DXF o IFC)" })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^Agregar fila/ }).length).toBeGreaterThan(0);
    await irA("Presupuesto");
    expect(screen.getByRole("button", { name: "Agregar partida" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Quitar OC-EXC/ })).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: /^Volver a la calculada/ }).length).toBeGreaterThan(0);
    expect(camposQueEscriben().length).toBeGreaterThan(0);
    await irA("APU");
    expect(screen.getByRole("button", { name: "Agregar línea" })).toBeInTheDocument();
    await irA("Plan y curva");
    expect(screen.getByRole("button", { name: "Plan desde los rendimientos" })).toBeInTheDocument();
    await irA("Parámetros");
    expect(await screen.findByRole("button", { name: "Convertir la moneda…" })).toBeInTheDocument();
    await irA("Trazabilidad");
    expect(await screen.findByRole("button", { name: "Restaurar una versión…" })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Enviar a aprobación…" })).toBeInTheDocument());
  });

  test("con un borrador de solo lectura tampoco se pintan los controles que escriben", async () => {
    servidor(true);
    montar(ACCIONES_ARMA);
    expect(await screen.findByRole("note")).toHaveTextContent("Está viendo este presupuesto en solo lectura.");
    await irA("Presupuesto");
    expect(botonesQueEscriben()).toEqual([]);
    expect(camposQueEscriben()).toEqual([]);
  });
});
