import { configure, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import { formulariosSucios, olvidarFormularios } from "../../shell/sucio";
import type { Aplicacion } from "../../shell/contexto";
import { informeAuditoria, vistaApu, vistaEspacio, vistaParametros } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, DetalleApu, Resumen, VersionesRespuesta, VistaApu, VistaParametros } from "./logica";
import type { InsumoCandidato, InsumosRespuesta } from "./logicaApu";

// Tarea 26 (MP-7): en la pestaña APU de una versión se agregan y se quitan líneas. El servidor se simula con la forma del
// contrato: `POST …/apu/{partida}/lineas` con `{rev, tipo, insumo, descripcion, unidad, cantidad, precio, depreciacion,
// modalidad}` (un insumo de la lista de la versión por su código, o uno nuevo con su descripción, unidad y precio) y
// `POST …/apu/{partida}/lineas/quitar` con `{rev, tipo, indice}`; las dos responden `{rev, resumen, apu}`; 422 con el
// `detalle` de la hoja; 409 por `rev` viejo. Datos ficticios (AF-LLAVE de OF-001 y la vivienda de la obra).
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
  acciones: ["editar_hoja"],
  modo_entrega: false,
};

const ID = "id-borrador-aaaaaaaaaaaa";
const REV_VIEJO = "El borrador cambió en otra ventana: vuelva a cargarlo.";
const UNA_LINEA = "Un APU necesita al menos una línea.";
const REGLA = "Use la coma para los decimales: por ejemplo 2,5. El punto separa los miles: 1.234,56.";
const VERSIONES: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "001",
  versiones: [{ codigo: "001", fecha: "2026-10-05", motivo: "", origen: "", vigente: true, descartada: false, cambios: 0 }],
};
const m = (texto: string, exacto = texto) => ({ texto, exacto });

function resumen(extra: Partial<Resumen> = {}): Resumen {
  return {
    rev: 0,
    moneda: "USD",
    total: m("2703.86", "2703.860232344044033333333333"),
    cambios: 0,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
    ...extra,
  };
}

function borrador(versionAbierta = true): BorradorAbierto {
  return {
    id: ID,
    base: {
      proyecto: "OF-001",
      version: versionAbierta ? "001" : null,
      vigente: "001",
      lista: "Lista",
      espacio_de: "001",
      solo_lectura: false,
      moneda: "USD",
    },
    resumen: resumen(),
    instantanea: { creadas: 0, mensaje: null },
  };
}

// El APU de AF-LLAVE con los materiales que se pidan (el resto, como en `datosDePrueba`).
function conMateriales(filas: Record<string, string>[], extra: Partial<DetalleApu> = {}): VistaApu {
  const base = vistaApu().detalle!;
  return vistaApu({
    detalle: { ...base, ...extra, grupos: base.grupos.map((g, i) => (i === 0 ? { ...g, filas } : g)) },
  });
}

const insumo = (codigo: string, descripcion: string, unidad: string, precio: string): InsumoCandidato => ({
  codigo,
  descripcion,
  unidad,
  precio: m(precio),
});
const MORTERO = insumo("MAT-020", "Mortero premezclado", "m2", "4.00");

type Cuerpo = Record<string, unknown> & { rev: number };

describe("Hoja de la obra: agregar y quitar líneas del APU de la versión (Tarea 26)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  let abierto: BorradorAbierto;
  let apu: VistaApu;
  let parametros: VistaParametros;
  let candidatos: (url: URL) => InsumosRespuesta | Response;
  let alPonerApu: (cuerpo: Cuerpo) => Response | Promise<Response>;
  let alAgregarLinea: (cuerpo: Cuerpo) => Response | Promise<Response>;
  let alQuitarLinea: (cuerpo: Cuerpo) => Response | Promise<Response>;

  const acepta = (cuerpo: Cuerpo) =>
    json({ rev: cuerpo.rev + 1, resumen: resumen({ rev: cuerpo.rev + 1, cambios: cuerpo.rev + 1 }), apu });

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    localStorage.clear();
    sessionStorage.clear();
    abierto = borrador();
    apu = vistaApu();
    parametros = vistaParametros();
    candidatos = () => ({ insumos: [MORTERO], hay_mas: false });
    alPonerApu = (c) => acepta(c);
    alAgregarLinea = (c) => acepta(c);
    alQuitarLinea = (c) => acepta(c);
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = new URL(String(ruta), "http://silice.local");
      const metodo = init?.method ?? "GET";
      const camino = decodeURIComponent(url.pathname);
      const cuerpo = () => JSON.parse(String(init?.body)) as Cuerpo;
      if (camino === "/v1/hoja/versiones") return json(VERSIONES);
      if (camino === "/v1/hoja/borradores" && metodo === "POST") return json(abierto, 201);
      if (camino === "/v1/hoja/borradores" && metodo === "GET") return json([]);
      if (camino === `/v1/hoja/borradores/${ID}` && metodo === "GET") {
        return json({ id: abierto.id, base: abierto.base, resumen: abierto.resumen });
      }
      if (metodo === "POST" && /\/apu\/AF-LLAVE\/lineas\/quitar$/.test(camino)) return alQuitarLinea(cuerpo());
      if (metodo === "POST" && /\/apu\/AF-LLAVE\/lineas$/.test(camino)) return alAgregarLinea(cuerpo());
      if (metodo === "PUT" && /\/apu\/AF-LLAVE$/.test(camino)) return alPonerApu(cuerpo());
      if (camino === `/v1/hoja/borradores/${ID}/insumos`) {
        const r = candidatos(url);
        return r instanceof Response ? r : json(r);
      }
      if (camino.endsWith("/vistas/apu")) return json(apu);
      if (camino.endsWith("/vistas/espacio")) return json(vistaEspacio());
      if (camino.endsWith("/vistas/parametros")) return json(parametros);
      if (camino.endsWith("/vistas/auditoria")) return json(informeAuditoria());
      return new Response(null, { status: 204 });
    });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  const llamadasA = (metodo: string, patron: RegExp) =>
    fetchFalso.mock.calls.filter(([r, init]) => (init?.method ?? "GET") === metodo && patron.test(decodeURIComponent(String(r))));
  const cuerposDe = (metodo: string, patron: RegExp): Cuerpo[] =>
    llamadasA(metodo, patron).map(([, init]) => JSON.parse(String(init?.body)) as Cuerpo);
  const altas = () => cuerposDe("POST", /\/apu\/AF-LLAVE\/lineas$/);
  const bajas = () => cuerposDe("POST", /\/apu\/AF-LLAVE\/lineas\/quitar$/);
  const escriturasDeApu = () => cuerposDe("PUT", /\/apu\/AF-LLAVE$/);
  const urlsDeInsumos = () => fetchFalso.mock.calls.map(([r]) => String(r)).filter((u) => u.includes("/insumos?"));

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

  async function irAApu() {
    montar();
    await screen.findByRole("region", { name: "Estado del borrador" });
    await userEvent.click(screen.getByRole("tab", { name: "Análisis de precio (APU)" }));
    await screen.findByRole("textbox", { name: "Cantidad, Materiales fila 1" });
  }

  const regionDeEstado = () => screen.getByRole("region", { name: "Estado del borrador" });
  const campo = (nombre: string | RegExp) => screen.getByRole("textbox", { name: nombre });
  const dialogo = () => screen.getByRole("dialog", { name: "Agregar línea al APU" });

  async function abrirDialogo() {
    await userEvent.click(screen.getByRole("button", { name: "Agregar línea" }));
    return dialogo();
  }

  // Escribe en el buscador del insumo y elige la opción (`nombre`) de la lista que aparece tras la pausa.
  async function elegirEnElBuscador(texto: string, nombre: string | RegExp) {
    const u = userEvent.setup();
    await u.type(within(dialogo()).getByRole("combobox", { name: "Insumo" }), texto);
    await u.click(await screen.findByRole("option", { name: nombre }));
  }

  // --- agregar ------------------------------------------------------------------------------------------------------------

  test("«Agregar línea» abre un diálogo con el foco en el insumo; Esc lo cierra y el foco vuelve al botón", async () => {
    await irAApu();
    const caja = await abrirDialogo();
    expect(caja).toHaveAttribute("aria-modal", "true");
    expect(within(caja).getByRole("combobox", { name: "Insumo" })).toHaveFocus();
    expect(within(caja).getByRole("combobox", { name: "Tipo de línea" })).toHaveValue("material");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Agregar línea al APU" })).toBeNull();
    await vi.waitFor(() => expect(screen.getByRole("button", { name: "Agregar línea" })).toHaveFocus());
    expect(altas()).toHaveLength(0);
  });

  test("un insumo de la lista de la versión: se busca por tipo, se ve su precio en es-VE y se manda su código", async () => {
    await irAApu();
    await abrirDialogo();
    await elegirEnElBuscador("mort", /Mortero premezclado/);
    expect(urlsDeInsumos().some((u) => /tipo=material/.test(u) && /texto=mort/.test(u))).toBe(true);
    expect(within(dialogo()).getByText("Precio de la lista de la versión: 4,00 USD por m2")).toBeInTheDocument();
    expect(within(dialogo()).queryByRole("textbox", { name: /Precio/ })).toBeNull(); // el precio no se teclea
    await userEvent.type(within(dialogo()).getByRole("textbox", { name: /^Cantidad/ }), "2");
    await userEvent.click(within(dialogo()).getByRole("button", { name: "Agregar al APU" }));
    await vi.waitFor(() => expect(altas()).toHaveLength(1));
    expect(altas()[0]).toEqual({
      rev: 0,
      tipo: "material",
      insumo: "MAT-020",
      descripcion: "",
      unidad: "",
      cantidad: "2",
      precio: "",
      depreciacion: "",
      modalidad: "jornal",
    });
    await vi.waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    expect(await screen.findByText("Se agregó «Mortero premezclado» a los materiales de AF-LLAVE.")).toBeInTheDocument();
    expect(within(regionDeEstado()).getByText(/· 1 cambio sin guardar/)).toBeInTheDocument();
  });

  test("un insumo nuevo: «Insumo nuevo «X»» pide unidad y precio, y todo viaja como texto tal cual", async () => {
    candidatos = () => ({ insumos: [], hay_mas: false });
    await irAApu();
    await abrirDialogo();
    await elegirEnElBuscador("Concreto premezclado", "Insumo nuevo «Concreto premezclado»");
    const caja = dialogo();
    await userEvent.type(within(caja).getByRole("textbox", { name: "Unidad" }), "m3");
    await userEvent.type(within(caja).getByRole("textbox", { name: "Precio (USD)" }), "95,00");
    await userEvent.type(within(caja).getByRole("textbox", { name: /^Cantidad/ }), "1,05");
    await userEvent.click(within(caja).getByRole("button", { name: "Agregar al APU" }));
    await vi.waitFor(() => expect(altas()).toHaveLength(1));
    expect(altas()[0]).toEqual({
      rev: 0,
      tipo: "material",
      insumo: "",
      descripcion: "Concreto premezclado",
      unidad: "m3",
      cantidad: "1,05",
      precio: "95,00",
      depreciacion: "",
      modalidad: "jornal",
    });
  });

  test("un equipo nuevo pide la depreciación; la mano de obra, la modalidad y el jornal", async () => {
    candidatos = () => ({ insumos: [], hay_mas: false });
    await irAApu();
    await abrirDialogo();
    await userEvent.selectOptions(within(dialogo()).getByRole("combobox", { name: "Tipo de línea" }), "equipo");
    await elegirEnElBuscador("Vibrador", "Insumo nuevo «Vibrador»");
    expect(within(dialogo()).queryByRole("textbox", { name: "Unidad" })).toBeNull();
    await userEvent.type(within(dialogo()).getByRole("textbox", { name: "Precio (USD)" }), "30");
    await userEvent.type(within(dialogo()).getByRole("textbox", { name: /^Depreciación/ }), "0,5");
    await userEvent.type(within(dialogo()).getByRole("textbox", { name: /^Cantidad/ }), "1");
    await userEvent.click(within(dialogo()).getByRole("button", { name: "Agregar al APU" }));
    await vi.waitFor(() => expect(altas()).toHaveLength(1));
    expect(altas()[0]).toMatchObject({ tipo: "equipo", descripcion: "Vibrador", precio: "30", depreciacion: "0,5" });
    expect(urlsDeInsumos().some((u) => /tipo=equipo/.test(u))).toBe(true);
  });

  test("la mano de obra a destajo cambia el rótulo del precio y manda la modalidad", async () => {
    candidatos = () => ({ insumos: [], hay_mas: false });
    await irAApu();
    await abrirDialogo();
    await userEvent.selectOptions(within(dialogo()).getByRole("combobox", { name: "Tipo de línea" }), "mano_obra");
    await elegirEnElBuscador("Cuadrilla", "Insumo nuevo «Cuadrilla»");
    expect(within(dialogo()).getByRole("textbox", { name: "Jornal diario (USD)" })).toBeInTheDocument();
    await userEvent.selectOptions(within(dialogo()).getByRole("combobox", { name: "Modalidad" }), "destajo");
    await userEvent.type(within(dialogo()).getByRole("textbox", { name: "Precio por unidad de la partida (USD)" }), "12");
    await userEvent.type(within(dialogo()).getByRole("textbox", { name: /^Cantidad/ }), "1");
    await userEvent.click(within(dialogo()).getByRole("button", { name: "Agregar al APU" }));
    await vi.waitFor(() => expect(altas()).toHaveLength(1));
    expect(altas()[0]).toMatchObject({ tipo: "mano_obra", modalidad: "destajo", precio: "12" });
  });

  test("el diálogo cuenta como formulario sucio también con solo la depreciación o la modalidad", async () => {
    olvidarFormularios();
    await irAApu();
    await abrirDialogo();
    expect(formulariosSucios()).toEqual([]);
    await userEvent.selectOptions(within(dialogo()).getByRole("combobox", { name: "Tipo de línea" }), "equipo");
    await userEvent.type(within(dialogo()).getByRole("textbox", { name: /^Depreciación/ }), "0,5");
    await vi.waitFor(() => expect(formulariosSucios()).toEqual(["hoja"]));
    await userEvent.clear(within(dialogo()).getByRole("textbox", { name: /^Depreciación/ }));
    await vi.waitFor(() => expect(formulariosSucios()).toEqual([]));
    await userEvent.selectOptions(within(dialogo()).getByRole("combobox", { name: "Tipo de línea" }), "mano_obra");
    await userEvent.selectOptions(within(dialogo()).getByRole("combobox", { name: "Modalidad" }), "destajo");
    await vi.waitFor(() => expect(formulariosSucios()).toEqual(["hoja"]));
    olvidarFormularios();
  });

  test("lo escrito en un campo que el cambio de tipo oculta ya no cuenta como formulario sucio", async () => {
    olvidarFormularios();
    await irAApu();
    await abrirDialogo();
    await userEvent.selectOptions(within(dialogo()).getByRole("combobox", { name: "Tipo de línea" }), "equipo");
    await userEvent.type(within(dialogo()).getByRole("textbox", { name: /^Depreciación/ }), "0,5");
    await vi.waitFor(() => expect(formulariosSucios()).toEqual(["hoja"]));
    await userEvent.selectOptions(within(dialogo()).getByRole("combobox", { name: "Tipo de línea" }), "material");
    await vi.waitFor(() => expect(formulariosSucios()).toEqual([]));
    await userEvent.selectOptions(within(dialogo()).getByRole("combobox", { name: "Tipo de línea" }), "mano_obra");
    await userEvent.selectOptions(within(dialogo()).getByRole("combobox", { name: "Modalidad" }), "destajo");
    await vi.waitFor(() => expect(formulariosSucios()).toEqual(["hoja"]));
    await userEvent.selectOptions(within(dialogo()).getByRole("combobox", { name: "Tipo de línea" }), "material");
    await vi.waitFor(() => expect(formulariosSucios()).toEqual([]));
    olvidarFormularios();
  });

  test("sin elegir un insumo no se manda nada y el error va al buscador", async () => {
    await irAApu();
    await abrirDialogo();
    await userEvent.click(within(dialogo()).getByRole("button", { name: "Agregar al APU" }));
    expect(altas()).toHaveLength(0);
    const buscador = within(dialogo()).getByRole("combobox", { name: "Insumo" });
    expect(buscador).toHaveAttribute("aria-invalid", "true");
    expect(within(dialogo()).getByText("Elija un insumo de la lista o escriba uno nuevo con «Insumo nuevo».")).toBeInTheDocument();
    await vi.waitFor(() => expect(buscador).toHaveFocus());
  });

  test.each([
    [`La cantidad no se entiende como número. ${REGLA}`, /^Cantidad/],
    [`El precio no se entiende como número. ${REGLA}`, "Precio (USD)"],
    ["Escriba la unidad del material, por ejemplo m3.", "Unidad"],
  ])("un 422 «%s» va a su campo, el diálogo sigue abierto y el foco va al campo", async (detalle, nombre) => {
    candidatos = () => ({ insumos: [], hay_mas: false });
    alAgregarLinea = () => json({ detalle }, 422);
    await irAApu();
    await abrirDialogo();
    await elegirEnElBuscador("Concreto", "Insumo nuevo «Concreto»");
    await userEvent.type(within(dialogo()).getByRole("textbox", { name: /^Cantidad/ }), "1.05");
    await userEvent.click(within(dialogo()).getByRole("button", { name: "Agregar al APU" }));
    const destino = within(dialogo()).getByRole("textbox", { name: nombre });
    await vi.waitFor(() => expect(destino).toHaveAttribute("aria-invalid", "true"));
    expect(within(dialogo()).getByText(detalle)).toBeInTheDocument();
    await vi.waitFor(() => expect(destino).toHaveFocus());
    expect(within(regionDeEstado()).getByText(/Sin cambios sin guardar/)).toBeInTheDocument();
  });

  test("un 409 por rev viejo se dice en el diálogo, se vuelve a leer el borrador y el segundo intento lleva el rev releído", async () => {
    alAgregarLinea = () => json({ detalle: REV_VIEJO }, 409);
    await irAApu();
    await abrirDialogo();
    await elegirEnElBuscador("mort", /Mortero premezclado/);
    await userEvent.type(within(dialogo()).getByRole("textbox", { name: /^Cantidad/ }), "2");
    abierto = { ...abierto, resumen: resumen({ rev: 4, cambios: 2 }) };
    await userEvent.click(within(dialogo()).getByRole("button", { name: "Agregar al APU" }));
    expect(
      await within(dialogo()).findByText(`${REV_VIEJO} Ya se volvió a leer el borrador: puede agregar la línea otra vez.`),
    ).toBeInTheDocument();
    await vi.waitFor(() => expect(within(regionDeEstado()).getByText(/· 2 cambios sin guardar/)).toBeInTheDocument());
    alAgregarLinea = (c) => acepta(c);
    await userEvent.click(within(dialogo()).getByRole("button", { name: "Agregar al APU" }));
    await vi.waitFor(() => expect(altas()).toHaveLength(2));
    expect(altas()[1]!.rev).toBe(4);
  });

  test("agregar con una cantidad en la pausa: primero sale la edición y la línea lleva el rev que contestó", async () => {
    await irAApu();
    fireEvent.change(campo("Cantidad, Equipos fila 1"), { target: { value: "3" } });
    await abrirDialogo();
    await elegirEnElBuscador("mort", /Mortero premezclado/);
    await userEvent.type(within(dialogo()).getByRole("textbox", { name: /^Cantidad/ }), "2");
    await userEvent.click(within(dialogo()).getByRole("button", { name: "Agregar al APU" }));
    await vi.waitFor(() => expect(altas()).toHaveLength(1));
    expect(escriturasDeApu()).toEqual([{ rev: 0, rendimiento: "20", materiales: ["1"], equipos: ["3"], mano_obra: ["1", "1"] }]);
    expect(altas()[0]!.rev).toBe(1);
  });

  test("tras agregar, la tabla de la línea nueva viaja con el APU: la siguiente edición manda una cantidad más", async () => {
    await irAApu();
    apu = conMateriales([
      { descripcion: "Llave de bola PVC 1/2", unidad: "pieza", cantidad: "1", precio: "7,7483" },
      { descripcion: "Mortero premezclado", unidad: "m2", cantidad: "2", precio: "4,00" },
    ]);
    await abrirDialogo();
    await elegirEnElBuscador("mort", /Mortero premezclado/);
    await userEvent.type(within(dialogo()).getByRole("textbox", { name: /^Cantidad/ }), "2");
    await userEvent.click(within(dialogo()).getByRole("button", { name: "Agregar al APU" }));
    await screen.findByRole("textbox", { name: "Cantidad, Materiales fila 2" });
    fireEvent.change(campo("Cantidad, Materiales fila 2"), { target: { value: "2,5" } });
    await vi.waitFor(() => expect(escriturasDeApu()).toHaveLength(1));
    expect(escriturasDeApu()[0]).toEqual({
      rev: 1,
      rendimiento: "20",
      materiales: ["1", "2,5"],
      equipos: ["1"],
      mano_obra: ["1", "1"],
    });
  });

  // --- quitar -------------------------------------------------------------------------------------------------------------

  test("«Quitar» de una línea pide confirmación y manda el tipo y el índice desde 0", async () => {
    await irAApu();
    await userEvent.click(screen.getByRole("button", { name: "Quitar Ayudante N2, Mano de obra fila 2" }));
    const confirmar = screen.getByRole("alertdialog", { name: "Quitar línea" });
    expect(confirmar).toHaveTextContent(
      "¿Quitar «Ayudante N2» de la mano de obra de AF-LLAVE? Lo puede descartar antes de guardar.",
    );
    await userEvent.click(within(confirmar).getByRole("button", { name: "Quitar" }));
    await vi.waitFor(() => expect(bajas()).toEqual([{ rev: 0, tipo: "mano_obra", indice: 1 }]));
    expect(await screen.findByText("Se quitó «Ayudante N2» de la mano de obra de AF-LLAVE.")).toBeInTheDocument();
    expect(within(regionDeEstado()).getByText(/· 1 cambio sin guardar/)).toBeInTheDocument();
  });

  test("cancelar la confirmación no manda nada y devuelve el foco al botón de la línea", async () => {
    await irAApu();
    const boton = screen.getByRole("button", { name: "Quitar Llave de bola PVC 1/2, Materiales fila 1" });
    await userEvent.click(boton);
    await userEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Cancelar" }));
    await vi.waitFor(() => expect(boton).toHaveFocus());
    expect(bajas()).toHaveLength(0);
  });

  test("quitar con una cantidad en la pausa: sale primero la edición; después, la tabla viaja sin la línea quitada", async () => {
    await irAApu();
    fireEvent.change(campo("Cantidad, Mano de obra fila 2"), { target: { value: "3" } });
    apu = conMateriales([]);
    await userEvent.click(screen.getByRole("button", { name: "Quitar Llave de bola PVC 1/2, Materiales fila 1" }));
    await userEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Quitar" }));
    await vi.waitFor(() => expect(bajas()).toHaveLength(1));
    expect(escriturasDeApu()).toEqual([{ rev: 0, rendimiento: "20", materiales: ["1"], equipos: ["1"], mano_obra: ["1", "3"] }]);
    expect(bajas()[0]).toEqual({ rev: 1, tipo: "material", indice: 0 });
    await screen.findByText("Se quitó «Llave de bola PVC 1/2» de los materiales de AF-LLAVE.");
    fireEvent.change(campo("Cantidad, Mano de obra fila 1"), { target: { value: "2" } });
    await vi.waitFor(() => expect(escriturasDeApu()).toHaveLength(2));
    expect(escriturasDeApu()[1]).toEqual({ rev: 2, rendimiento: "20", materiales: [], equipos: ["1"], mano_obra: ["2", "3"] });
  });

  test("quitar la última línea: el 422 se dice tal cual en el aviso del APU y la tabla no cambia", async () => {
    alQuitarLinea = () => json({ detalle: UNA_LINEA }, 422);
    await irAApu();
    await userEvent.click(screen.getByRole("button", { name: "Quitar Llave de bola PVC 1/2, Materiales fila 1" }));
    await userEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Quitar" }));
    const alerta = await screen.findByText(UNA_LINEA);
    expect(alerta.closest("[role='alert']")).not.toBeNull();
    expect(campo("Cantidad, Materiales fila 1")).toHaveValue("1");
    expect(within(regionDeEstado()).getByText(/Sin cambios sin guardar/)).toBeInTheDocument();
  });

  // --- sin versión y textos -----------------------------------------------------------------------------------------------

  test("sin versión guardada no se ofrece agregar ni quitar líneas, y se dice por qué", async () => {
    abierto = borrador(false);
    apu = vistaApu({ detalle: { ...vistaApu().detalle!, solo_lectura_insumos: true } });
    await irAApu();
    expect(screen.queryByRole("button", { name: "Agregar línea" })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Quitar / })).toBeNull();
    expect(screen.getByText("Las líneas del APU se agregan y se quitan en una versión guardada.")).toBeInTheDocument();
  });

  test("la ayuda del APU dice la regla de la coma y que también se agregan y se quitan líneas", async () => {
    await irAApu();
    await userEvent.click(screen.getByRole("button", { name: "¿Qué es esto?" })); // baja 25: la ayuda va plegada
    expect(screen.queryByText(/la coma no se acepta/)).toBeNull();
    expect(screen.getByText(/Escriba los decimales con coma: 2,5; el punto separa los miles: 1\.234,56\./)).toBeInTheDocument();
    expect(screen.getByText(/agregar una línea \(un insumo de la lista de la versión o uno nuevo con su precio\)/)).toBeInTheDocument();
  });

  test("agregar y quitar no dejan nada en localStorage ni sessionStorage", async () => {
    await irAApu();
    await userEvent.click(screen.getByRole("button", { name: "Quitar Ayudante N2, Mano de obra fila 2" }));
    await userEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Quitar" }));
    await vi.waitFor(() => expect(bajas()).toHaveLength(1));
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  test("los archivos de las líneas del APU no convierten cifras (sin Number, parseFloat, toFixed ni + unario)", () => {
    const fuentes = import.meta.glob("./*.{ts,tsx}", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
    for (const ruta of ["./logicaApu.ts", "./PestanaApu.tsx", "./AgregarLineaApu.tsx"]) {
      expect(Object.keys(fuentes), ruta).toContain(ruta);
      expect(fuentes[ruta], ruta).not.toMatch(
        /\bNumber\s*\(|\bparseFloat\s*\(|\bparseInt\s*\(|\.toFixed\s*\(|(?:[=(,:?]|\breturn)\s*\+\s*[A-Za-z_$(]/,
      );
    }
  });
});
