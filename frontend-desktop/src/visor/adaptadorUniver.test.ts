// D-3 (MOD-5): al salir de «Libro de la empresa» la pagina lanzaba `[redi]: Cannot find "u4" registered by any
// injector`. En el paquete construido, `u4` es el controlador de zoom de cada hoja de Univer: lo pide la operacion
// `sheet.operation.set-zoom-ratio` (la que corre `FWorksheet.zoom`) con `renderUnit.with(u4)`, y falla cuando el
// inyector de la hoja ya se esta desechando. Univer no dibuja en jsdom, asi que aqui se reemplaza por un doble que se
// comporta como el real en lo que importa: despues de desecharse, tocar su fachada lanza ese mismo error, y desechar
// la instancia con la hoja (la unidad) todavia viva tambien lo lanza.
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { LibroVisualRespuesta } from "../api/tipos";

const doble = vi.hoisted(() => {
  const estado = {
    // Lo que se llamo, en orden, al desechar.
    orden: [] as string[],
    unidadViva: true,
    instanciaViva: true,
    // true: desechar la instancia lanza siempre (aunque la unidad ya se haya ido).
    lanzaSiempre: false,
    // false: desechar la instancia con la unidad viva no lanza (para aislar los avisos pendientes).
    lanzaConUnidadViva: true,
    alEjecutarComando: null as null | (() => void),
  };
  const vigente = () => {
    if (!estado.instanciaViva || !estado.unidadViva) throw new Error('[redi]: Cannot find "u4" registered by any injector.');
  };
  const hoja = (nombre: string) => ({
    getSheetName: () => (vigente(), nombre),
    getSkeleton: () => (vigente(), {}),
    zoom: () => vigente(),
    getZoom: () => (vigente(), 1),
    getRange: () => ({ activate: () => vigente() }),
  });
  let activa = hoja("PRESUPUESTO");
  const fLibro = {
    getId: () => "libro-1",
    getActiveSheet: () => (vigente(), activa),
    getSheetByName: (n: string) => (vigente(), hoja(n)),
    setActiveSheet: (h: ReturnType<typeof hoja>) => {
      vigente();
      activa = h;
    },
    getSheets: () => (vigente(), [activa]),
    setEditable: () => vigente(),
    onSelectionChange: () => ({ dispose: () => estado.orden.push("suscripcion") }),
  };
  const unidadDeDibujo = {
    scene: {
      getViewport: () => ({ onScrollAfter$: { subscribeEvent: () => ({ unsubscribe: () => estado.orden.push("suscripcion") }) } }),
      // La escena dice 1: distinta de la razon pedida (1,25), asi que un aviso pendiente reaplicaria el zoom.
      getAncestorScale: () => ({ scaleX: 1, scaleY: 1 }),
    },
  };
  const servicios: Record<string, unknown> = {
    IRenderManagerService: { getRenderUnitById: () => (vigente(), unidadDeDibujo) },
    ICommandService: {
      onCommandExecuted: (f: () => void) => {
        estado.alEjecutarComando = f;
        return { dispose: () => estado.orden.push("suscripcion") };
      },
    },
    IConfigService: { setConfig: () => vigente() },
  };
  const univer = {
    __getInjector: () => ({ get: (clave: string) => servicios[clave] }),
    dispose: () => {
      estado.orden.push("instancia");
      const conUnidad = estado.unidadViva;
      estado.instanciaViva = false;
      if (estado.lanzaSiempre || (conUnidad && estado.lanzaConUnidadViva)) throw new Error('[redi]: Cannot find "u4" registered by any injector.');
    },
  };
  const univerAPI = {
    createWorkbook: () => fLibro,
    disposeUnit: (id: string) => {
      estado.orden.push(`unidad:${id}`);
      estado.unidadViva = false;
      return true;
    },
  };
  const reiniciar = () => {
    estado.orden = [];
    estado.unidadViva = true;
    estado.instanciaViva = true;
    estado.lanzaSiempre = false;
    estado.lanzaConUnidadViva = true;
    estado.alEjecutarComando = null;
    activa = hoja("PRESUPUESTO");
  };
  return { estado, univer, univerAPI, reiniciar };
});

vi.mock("@univerjs/preset-sheets-core/lib/index.css", () => ({}));
vi.mock("@univerjs/preset-sheets-core/locales/es-ES", () => ({ default: {} }));
vi.mock("@univerjs/preset-sheets-core", () => ({
  IRenderManagerService: "IRenderManagerService",
  SHEET_VIEWPORT_KEY: { VIEW_MAIN: "viewMain" },
  SHEETS_UI_PLUGIN_CONFIG_KEY: "sheets-ui.config",
  UniverSheetsCorePreset: () => ({ plugins: [] }),
}));
vi.mock("@univerjs/presets", () => ({
  createUniver: () => ({ univer: doble.univer, univerAPI: doble.univerAPI }),
  ICommandService: "ICommandService",
  IConfigService: "IConfigService",
  LocaleType: { ES_ES: "esES" },
  mergeLocales: (x: unknown) => x,
}));
vi.mock("../replica/aUniver", () => ({ aUniver: () => ({}) }));

const { crearHojaUniver } = await import("./adaptadorUniver");

const libro = {
  hojas: [
    { nombre: "PRESUPUESTO", visible: true },
    { nombre: "APU", visible: true },
  ],
} as unknown as LibroVisualRespuesta;

describe("adaptador de Univer: montar y desmontar (D-3)", () => {
  let cuadros: Map<number, FrameRequestCallback>;

  // Corre los cuadros de dibujo que queden pedidos, como haria el navegador.
  const correrCuadros = () => {
    const pendientes = [...cuadros.values()];
    cuadros.clear();
    pendientes.forEach((f) => f(0));
  };

  beforeEach(() => {
    doble.reiniciar();
    cuadros = new Map();
    let siguiente = 1;
    vi.stubGlobal("requestAnimationFrame", (f: FrameRequestCallback) => {
      const id = siguiente++;
      cuadros.set(id, f);
      return id;
    });
    vi.stubGlobal("cancelAnimationFrame", (id: number) => cuadros.delete(id));
    vi.stubGlobal(
      "ResizeObserver",
      class {
        observe() {}
        disconnect() {}
      },
    );
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  test("destruir desecha la hoja del libro antes que la instancia de Univer y no lanza", async () => {
    const visor = await crearHojaUniver(document.createElement("div"), libro, 1.25);
    expect(() => visor.destruir()).not.toThrow();
    const desechos = doble.estado.orden.filter((paso) => paso !== "suscripcion");
    expect(desechos).toEqual(["unidad:libro-1", "instancia"]);
    // Las suscripciones a Univer se sueltan antes de desecharlo.
    expect(doble.estado.orden.indexOf("suscripcion")).toBeLessThan(doble.estado.orden.indexOf("unidad:libro-1"));
  });

  test("un cuadro de dibujo que quedo pedido al destruir no vuelve a tocar Univer", async () => {
    doble.estado.lanzaConUnidadViva = false;
    const visor = await crearHojaUniver(document.createElement("div"), libro, 1.25);
    // Un comando de Univer justo antes de salir deja un aviso pendiente para el cuadro siguiente.
    doble.estado.alEjecutarComando?.();
    expect(cuadros.size).toBeGreaterThan(0);
    visor.destruir();
    expect(() => correrCuadros()).not.toThrow();
  });

  test("ir a una celda de otra hoja y salir antes de que se coloque no toca Univer despues", async () => {
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    doble.estado.lanzaConUnidadViva = false;
    const visor = await crearHojaUniver(document.createElement("div"), libro, 1);
    visor.irA({ hoja: "APU", fila0: 3, columna0: 2 });
    visor.destruir();
    expect(() => vi.runAllTimers()).not.toThrow();
    expect(() => correrCuadros()).not.toThrow();
  });

  test("si Univer lanza al desecharse, destruir no lo deja escapar y se puede llamar dos veces", async () => {
    doble.estado.lanzaSiempre = true;
    const aviso = vi.spyOn(console, "warn").mockImplementation(() => {});
    const visor = await crearHojaUniver(document.createElement("div"), libro, 1);
    expect(() => visor.destruir()).not.toThrow();
    expect(() => visor.destruir()).not.toThrow();
    // La segunda llamada no vuelve a desechar nada.
    expect(doble.estado.orden.filter((paso) => paso === "instancia")).toHaveLength(1);
    // No se calla: queda como aviso en la consola (no como error de pagina).
    expect(aviso).toHaveBeenCalledTimes(1);
    aviso.mockRestore();
  });

  test("despues de destruir, pedir zoom u hoja no toca Univer", async () => {
    doble.estado.lanzaConUnidadViva = false;
    const visor = await crearHojaUniver(document.createElement("div"), libro, 1);
    visor.destruir();
    expect(() => visor.fijarZoom(1.5)).not.toThrow();
    expect(() => visor.irAHoja("APU")).not.toThrow();
    expect(() => correrCuadros()).not.toThrow();
  });
});
