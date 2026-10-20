import { act, configure, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { informeAuditoria, vistaApu, vistaParametros } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, DetalleApu, Resumen, VersionesRespuesta, VistaApu, VistaParametros } from "./logica";
import type { InsumoCandidato, InsumosRespuesta } from "./logicaApu";

// Rebanada 3c-3: el APU de una partida se edita (cantidades por línea y rendimiento) y se cambia el insumo de una línea.
// El servidor se simula con respuestas ficticias con la forma del contrato (diseño §4.4): E6 `PUT …/apu/{partida}` con
// `{rev, rendimiento, materiales, equipos, mano_obra}`, E7 `POST …/apu/{partida}/insumo` con `{rev, tipo, indice, insumo}`
// y E8 `GET …/insumos?tipo=&texto=&limite=` -> `{insumos, hay_mas}`; todas con respuesta `{rev, resumen, apu}`; 422 con el
// `detalle` de la clásica; 409 por `rev` viejo. Caso ficticio OF-001; los literales son de su memoria y del diseño.
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

function borrador(extra: Partial<Resumen> = {}, versionAbierta = true): BorradorAbierto {
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
    resumen: resumen(extra),
    instantanea: { creadas: 0, mensaje: null },
  };
}

// El APU de otra partida (AF-CODO-1/2: el código trae «/», que va codificado en la ruta).
function detalleDeCodo(): DetalleApu {
  const base = vistaApu().detalle!;
  return {
    ...base,
    codigo: "AF-CODO-1/2",
    descripcion: "Codo PVC 1/2",
    unidad: "pieza",
    rendimiento: "40",
    grupos: [
      { ...base.grupos[0]!, filas: [{ descripcion: "Codo de PVC 1/2", unidad: "pieza", cantidad: "2", precio: "0.5" }], subtotal: m("1.00") },
      { ...base.grupos[1]!, filas: [], subtotal: m("0.00") },
      { ...base.grupos[2]!, filas: [{ descripcion: "Plomero de 1ra N5", cantidad: "0.5", sueldo: "2.1877", modalidad: "jornal" }], subtotal: m("1.09") },
    ],
  };
}

const insumo = (codigo: string, descripcion: string, unidad: string, precio: string): InsumoCandidato => ({
  codigo,
  descripcion,
  unidad,
  precio: m(precio),
});
const MATERIALES: InsumosRespuesta = {
  insumos: [insumo("MAT-010", "Llave de bola PVC 3/4", "pieza", "8.10"), insumo("MAT-011", "Llave de bola PVC 1", "pieza", "11.25")],
  hay_mas: false,
};

type Cuerpo = Record<string, unknown> & { rev: number };

describe("Hoja del proyecto: APU editable y cambio de insumo (3c-3)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  let abierto: BorradorAbierto;
  let apu: VistaApu;
  let parametros: VistaParametros;
  let candidatos: (url: URL) => InsumosRespuesta | Response;
  let alPonerApu: (cuerpo: Cuerpo, partida: string) => Response | Promise<Response>;
  let alCambiarInsumo: (cuerpo: Cuerpo, partida: string) => Response | Promise<Response>;
  let alPonerParametros: (cuerpo: Cuerpo) => Response | Promise<Response>;

  const acepta = (cuerpo: Cuerpo, extra: Partial<Resumen> = {}) =>
    json({ rev: cuerpo.rev + 1, resumen: resumen({ rev: cuerpo.rev + 1, cambios: 1, total: m("2800.50", "2800.5"), ...extra }), apu, parametros });

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    localStorage.clear();
    sessionStorage.clear();
    abierto = borrador();
    apu = vistaApu();
    parametros = vistaParametros();
    candidatos = () => MATERIALES;
    alPonerApu = (c) => acepta(c);
    alCambiarInsumo = (c) => acepta(c);
    alPonerParametros = (c) => acepta(c);
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = new URL(String(ruta), "http://silice.local");
      const metodo = init?.method ?? "GET";
      const camino = decodeURIComponent(url.pathname);
      if (camino === "/v1/hoja/versiones") return json(VERSIONES);
      if (camino === "/v1/hoja/borradores" && metodo === "POST") return json(abierto, 201);
      if (camino === "/v1/hoja/borradores" && metodo === "GET") return json([]);
      if (camino === `/v1/hoja/borradores/${ID}` && metodo === "GET") {
        return json({ id: abierto.id, base: abierto.base, resumen: abierto.resumen });
      }
      const escribe = /^\/v1\/hoja\/borradores\/[^/]+\/apu\/(.+?)(\/insumo)?$/.exec(camino);
      if (escribe && (metodo === "PUT" || metodo === "POST")) {
        const cuerpo = JSON.parse(String(init?.body)) as Cuerpo;
        return escribe[2] ? alCambiarInsumo(cuerpo, escribe[1]!) : alPonerApu(cuerpo, escribe[1]!);
      }
      if (camino === `/v1/hoja/borradores/${ID}/parametros` && metodo === "PUT") {
        return alPonerParametros(JSON.parse(String(init?.body)) as Cuerpo);
      }
      if (camino === `/v1/hoja/borradores/${ID}/insumos`) {
        const r = candidatos(url);
        return r instanceof Response ? r : json(r);
      }
      if (camino.endsWith("/vistas/apu")) {
        const pedida = url.searchParams.get("partida");
        if (pedida === "AF-CODO-1/2") {
          return json({ ...apu, seleccionada: "AF-CODO-1/2", detalle: detalleDeCodo() });
        }
        return json(apu);
      }
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
  const escriturasDeApu = (): Cuerpo[] =>
    llamadasA("PUT", /\/apu\/[^/]+$/).map(([, init]) => JSON.parse(String(init?.body)) as Cuerpo);
  const escriturasDeInsumo = (): Cuerpo[] =>
    llamadasA("POST", /\/apu\/.+\/insumo$/).map(([, init]) => JSON.parse(String(init?.body)) as Cuerpo);
  const urlsDeInsumos = () => fetchFalso.mock.calls.map(([r]) => String(r)).filter((u) => u.includes("/insumos?"));
  const lecturasDeApu = () => fetchFalso.mock.calls.filter(([r]) => String(r).includes("/vistas/apu")).length;

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
    await userEvent.click(screen.getByRole("tab", { name: "APU" }));
    await screen.findByRole("textbox", { name: "Cantidad, Materiales fila 1" });
  }

  const avisos = () => screen.queryAllByRole("alert").filter((a) => (a.textContent ?? "") !== "");
  const aviso = () => {
    const todos = avisos();
    if (todos.length !== 1) throw new Error(`Se esperaba un aviso y hay ${todos.length}`);
    return todos[0]!;
  };
  const campo = (nombre: string | RegExp) => screen.getByRole("textbox", { name: nombre });
  const pausa = (ms: number) =>
    act(async () => {
      vi.advanceTimersByTime(ms);
    });
  const relojFalso = () => vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  const regionDeEstado = () => screen.getByRole("region", { name: "Estado del borrador" });

  // Con setTimeout simulado, `findBy*` y `waitFor` se cuelgan: se espera dando turnos a las promesas.
  async function esperar<T>(comprobar: () => T): Promise<T> {
    let ultimo: unknown;
    for (let i = 0; i < 300; i++) {
      try {
        return comprobar();
      } catch (e) {
        ultimo = e;
      }
      await act(async () => {
        await new Promise<void>((resolver) => setImmediate(resolver));
      });
    }
    throw ultimo;
  }

  // --- 3c-F11: edición de cantidades y rendimiento -----------------------------------------------------------------------

  test("cada línea tiene su cantidad editable con nombre accesible «Cantidad, {rubro} fila {n}», y el rendimiento también", async () => {
    await irAApu();
    expect(campo("Cantidad, Materiales fila 1")).toHaveValue("1");
    expect(campo("Cantidad, Equipos fila 1")).toHaveValue("1");
    expect(campo("Cantidad, Mano de obra fila 1")).toHaveValue("1");
    expect(campo("Cantidad, Mano de obra fila 2")).toHaveValue("1");
    expect(campo("Rendimiento (unidades por día)")).toHaveValue("20");
    // El resto de la línea es de solo lectura: la descripción y el precio se leen, no se editan.
    expect(screen.queryByRole("textbox", { name: /Descripción|Precio|Sueldo/ })).toBeNull();
    expect(screen.getByText("Llave de bola PVC 1/2")).toBeInTheDocument();
    expect(llamadasA("PUT", /\/apu\//)).toHaveLength(0); // nada sale hasta que la persona escribe
  });

  test("3c-F11 (E6): tras la pausa sale una sola petición con rev, rendimiento y las cantidades de las tres tablas, y se releen los subtotales", async () => {
    await irAApu();
    relojFalso();
    const lecturas = lecturasDeApu();
    apu = vistaApu({
      detalle: {
        ...vistaApu().detalle!,
        grupos: vistaApu().detalle!.grupos.map((g, i) => (i === 0 ? { ...g, subtotal: m("15.50", "15.5") } : g)),
      },
    });
    fireEvent.change(campo("Cantidad, Materiales fila 1"), { target: { value: "2.5" } });
    await pausa(399);
    expect(escriturasDeApu()).toHaveLength(0);
    await pausa(1);
    expect(escriturasDeApu()).toEqual([
      { rev: 0, rendimiento: "20", materiales: ["2.5"], equipos: ["1"], mano_obra: ["1", "1"] },
    ]);
    expect(llamadasA("PUT", /\/apu\/AF-LLAVE$/)).toHaveLength(1);
    await esperar(() => within(regionDeEstado()).getByText(/· 1 cambio sin guardar/));
    // El subtotal se vuelve a leer del servidor; lo escrito se queda como lo escribió la persona.
    await esperar(() => expect(lecturasDeApu()).toBeGreaterThan(lecturas));
    await esperar(() => screen.getByText("15,50"));
    expect(campo("Cantidad, Materiales fila 1")).toHaveValue("2.5");
  });

  test("el rendimiento y las cantidades de otro rubro viajan juntos; la coma decimal se manda tal cual (decide el servidor)", async () => {
    await irAApu();
    relojFalso();
    fireEvent.change(campo("Rendimiento (unidades por día)"), { target: { value: "25,5" } });
    fireEvent.change(campo("Cantidad, Mano de obra fila 2"), { target: { value: "0,5" } });
    await pausa(400);
    expect(escriturasDeApu()).toEqual([
      { rev: 0, rendimiento: "25,5", materiales: ["1"], equipos: ["1"], mano_obra: ["1", "0,5"] },
    ]);
  });

  test("varias teclas dentro de la pausa son una sola petición con lo último, y la siguiente lleva el rev nuevo", async () => {
    await irAApu();
    relojFalso();
    fireEvent.change(campo("Cantidad, Equipos fila 1"), { target: { value: "3" } });
    await pausa(300);
    fireEvent.change(campo("Cantidad, Equipos fila 1"), { target: { value: "3.5" } });
    await pausa(400);
    expect(escriturasDeApu()).toHaveLength(1);
    expect(escriturasDeApu()[0]!.equipos).toEqual(["3.5"]);
    await esperar(() => within(regionDeEstado()).getByText(/· 1 cambio sin guardar/));
    fireEvent.change(campo("Cantidad, Equipos fila 1"), { target: { value: "3.75" } });
    await pausa(400);
    expect(escriturasDeApu()).toHaveLength(2);
    expect(escriturasDeApu()[1]!.rev).toBe(1);
  });

  test("422 de una línea: «{detalle}. La hoja sigue con el último APU válido.» en un alert y solo esa celda queda inválida", async () => {
    await irAApu();
    relojFalso();
    const DETALLE = "mano de obra, fila 2: la cantidad no puede ser negativa";
    alPonerApu = () => json({ detalle: DETALLE }, 422);
    fireEvent.change(campo("Cantidad, Mano de obra fila 2"), { target: { value: "-1" } });
    await pausa(400);
    expect(await esperar(() => aviso())).toHaveTextContent(`${DETALLE}. La hoja sigue con el último APU válido.`);
    const invalida = campo("Cantidad, Mano de obra fila 2");
    await esperar(() => expect(invalida).toHaveAttribute("aria-invalid", "true"));
    expect(invalida).toHaveValue("-1"); // se queda lo escrito para corregirlo
    expect(document.getElementById(invalida.getAttribute("aria-describedby")!)).toHaveTextContent(DETALLE);
    expect(campo("Cantidad, Mano de obra fila 1")).not.toHaveAttribute("aria-invalid", "true");
    expect(campo("Rendimiento (unidades por día)")).not.toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Valor no válido")).toBeInTheDocument(); // el color no va solo
    // El total mostrado es el anterior y el borrador no avanzó.
    expect(within(regionDeEstado()).getByText(/Sin cambios sin guardar/)).toBeInTheDocument();
    // Corregir y volver a mandar: el rev sigue siendo el que el servidor no avanzó, y el alert desaparece.
    alPonerApu = (c) => acepta(c);
    fireEvent.change(invalida, { target: { value: "1" } });
    await pausa(400);
    await esperar(() => expect(escriturasDeApu()).toHaveLength(2));
    expect(escriturasDeApu()[1]!.rev).toBe(0);
    await esperar(() => expect(avisos()).toHaveLength(0));
  });

  test("422 del rendimiento: marca el campo del rendimiento y no una línea", async () => {
    await irAApu();
    relojFalso();
    const DETALLE = "rendimiento: 'mucho' no es un numero decimal valido";
    alPonerApu = () => json({ detalle: DETALLE }, 422);
    fireEvent.change(campo("Rendimiento (unidades por día)"), { target: { value: "mucho" } });
    await pausa(400);
    expect(await esperar(() => aviso())).toHaveTextContent(`${DETALLE}. La hoja sigue con el último APU válido.`);
    expect(campo("Rendimiento (unidades por día)")).toHaveAttribute("aria-invalid", "true");
    expect(campo("Cantidad, Materiales fila 1")).not.toHaveAttribute("aria-invalid", "true");
  });

  test("un 422 que no nombra rubro ni rendimiento se muestra completo y no marca ninguna celda", async () => {
    await irAApu();
    relojFalso();
    alPonerApu = () => json({ detalle: "El APU de AF-LLAVE no existe en este borrador" }, 422);
    fireEvent.change(campo("Cantidad, Equipos fila 1"), { target: { value: "2" } });
    await pausa(400);
    expect(await esperar(() => aviso())).toHaveTextContent("El APU de AF-LLAVE no existe en este borrador. La hoja sigue con el último APU válido.");
    expect(document.querySelector("[aria-invalid='true']")).toBeNull();
  });

  test("409 por rev viejo: avisa, ofrece recargar, no manda más y al recargar vuelve a sembrar las cantidades del servidor", async () => {
    await irAApu();
    relojFalso();
    alPonerApu = () => json({ detalle: REV_VIEJO }, 409);
    fireEvent.change(campo("Cantidad, Materiales fila 1"), { target: { value: "7" } });
    await pausa(400);
    expect(await esperar(() => aviso())).toHaveTextContent(REV_VIEJO);
    fireEvent.change(campo("Cantidad, Materiales fila 1"), { target: { value: "77" } });
    await pausa(800);
    expect(escriturasDeApu()).toHaveLength(1); // tras un 409 no se manda más hasta recargar
    // Otra ventana dejó el borrador en rev 5 con otra cantidad.
    abierto = borrador({ rev: 5, cambios: 3 });
    apu = vistaApu({
      detalle: {
        ...vistaApu().detalle!,
        grupos: vistaApu().detalle!.grupos.map((g, i) =>
          i === 0 ? { ...g, filas: [{ descripcion: "Llave de bola PVC 1/2", unidad: "pieza", cantidad: "9", precio: "7.7483" }] } : g,
        ),
      },
    });
    alPonerApu = (c) => acepta(c);
    fireEvent.click(screen.getByRole("button", { name: "Recargar el borrador" }));
    await esperar(() => expect(campo("Cantidad, Materiales fila 1")).toHaveValue("9"));
    expect(within(regionDeEstado()).getByText(/· 3 cambios sin guardar/)).toBeInTheDocument();
    expect(avisos()).toHaveLength(0);
    fireEvent.change(campo("Cantidad, Materiales fila 1"), { target: { value: "9.5" } });
    await pausa(400);
    await esperar(() => expect(escriturasDeApu()).toHaveLength(2));
    expect(escriturasDeApu()[1]!.rev).toBe(5);
  });

  test.each([
    ["el caso cambió", "El caso cambió desde que abrió este borrador: ábralo de nuevo en el caso actual."],
    ["ya se guardó", "Este borrador ya se guardó como la versión 002; abra esa versión para seguir."],
  ])("409 porque %s: recargar no sirve, se ofrece abrir de nuevo", async (_nombre, detalle) => {
    await irAApu();
    relojFalso();
    alPonerApu = () => json({ detalle }, 409);
    fireEvent.change(campo("Cantidad, Materiales fila 1"), { target: { value: "7" } });
    await pausa(400);
    expect(await esperar(() => aviso())).toHaveTextContent(detalle);
    expect(screen.queryByRole("button", { name: "Recargar el borrador" })).toBeNull();
    expect(screen.getByRole("button", { name: "Abrir de nuevo" })).toBeInTheDocument();
  });

  test("teclado: ↑ y ↓ pasan a la misma columna de la fila vecina del mismo rubro; Esc devuelve la celda a lo aceptado", async () => {
    await irAApu();
    const u = userEvent.setup({ delay: null });
    campo("Cantidad, Mano de obra fila 1").focus();
    await u.keyboard("{ArrowDown}");
    expect(campo("Cantidad, Mano de obra fila 2")).toHaveFocus();
    await u.keyboard("{ArrowUp}");
    expect(campo("Cantidad, Mano de obra fila 1")).toHaveFocus();
    await u.type(campo("Cantidad, Mano de obra fila 1"), "9");
    expect(campo("Cantidad, Mano de obra fila 1")).toHaveValue("19");
    await u.keyboard("{Escape}");
    expect(campo("Cantidad, Mano de obra fila 1")).toHaveValue("1");
  });

  test("cambiar de partida con una edición en la pausa la manda en seguida y siembra el editor con el APU de la otra (código con «/»)", async () => {
    await irAApu();
    relojFalso();
    fireEvent.change(campo("Cantidad, Materiales fila 1"), { target: { value: "4" } });
    fireEvent.click(screen.getByRole("radio", { name: /AF-CODO-1\/2/ }));
    await esperar(() => expect(escriturasDeApu()).toHaveLength(1));
    expect(llamadasA("PUT", /\/apu\/AF-LLAVE$/)).toHaveLength(1); // la edición pendiente era de AF-LLAVE
    await esperar(() => expect(campo("Rendimiento (unidades por día)")).toHaveValue("40"));
    expect(campo("Cantidad, Materiales fila 1")).toHaveValue("2");
    fireEvent.change(campo("Cantidad, Materiales fila 1"), { target: { value: "3" } });
    await pausa(400);
    await esperar(() => expect(escriturasDeApu()).toHaveLength(2));
    expect(fetchFalso.mock.calls.some(([r, i]) => i?.method === "PUT" && String(r) === `/v1/hoja/borradores/${ID}/apu/AF-CODO-1%2F2`)).toBe(true);
    expect(escriturasDeApu()[1]).toEqual({ rev: 1, rendimiento: "40", materiales: ["3"], equipos: [], mano_obra: ["0.5"] });
  });

  test("la búsqueda de partida sigue siendo del servidor y no pierde lo escrito en el editor", async () => {
    await irAApu();
    relojFalso();
    fireEvent.change(campo("Cantidad, Equipos fila 1"), { target: { value: "2" } });
    fireEvent.change(screen.getByRole("searchbox", { name: "Buscar partida" }), { target: { value: "codo" } });
    await pausa(300);
    await esperar(() => expect(fetchFalso.mock.calls.some(([r]) => String(r).includes("buscar=codo"))).toBe(true));
    expect(campo("Cantidad, Equipos fila 1")).toHaveValue("2");
  });

  // --- Factores de la versión (los cuatro parámetros, también aquí) -------------------------------------------------------

  test("los cuatro factores se editan en la pestaña (PUT …/parametros) y el cierre de la partida se vuelve a leer", async () => {
    await irAApu();
    relojFalso();
    expect(await esperar(() => campo(/^Administración/))).toHaveValue("0.15");
    expect(campo(/^FCAS/)).toHaveValue("6.00");
    const lecturas = lecturasDeApu();
    fireEvent.change(campo(/^Administración/), { target: { value: "0.20" } });
    await pausa(400);
    await esperar(() =>
      expect(
        fetchFalso.mock.calls.filter(([r, i]) => i?.method === "PUT" && String(r).endsWith("/parametros")).map(([, i]) => JSON.parse(String(i?.body))),
      ).toEqual([{ rev: 0, fcas: "6.00", bono_alimentacion: "5.8100", administracion: "0.20", utilidad: "0.10" }]),
    );
    await esperar(() => expect(lecturasDeApu()).toBeGreaterThan(lecturas));
  });

  // --- Estado de la partida --------------------------------------------------------------------------------------------

  test("el Estado de la partida muestra solo el texto del estado, sin el código crudo de la fila", async () => {
    apu = vistaApu({
      detalle: {
        ...vistaApu().detalle!,
        estados: ["Estado de AF-CODO-3/4|esp_fuentes:F1: ERROR: fuente F1: falta el origen"],
      },
    });
    await irAApu();
    expect(screen.getByText("ERROR: fuente F1: falta el origen")).toBeInTheDocument();
    expect(screen.queryByText(/Estado de AF-CODO/)).toBeNull();
    expect(screen.queryByText(/esp_fuentes:F1: ERROR/)).toBeNull();
  });

  // --- Cambio de insumo (E7, E8) ---------------------------------------------------------------------------------------

  const abrirInsumo = async () => {
    await userEvent.click(screen.getByRole("button", { name: "Cambiar el insumo de una línea (en la copia de esta versión)" }));
  };

  test("el cambio de insumo empieza plegado y no pide candidatos hasta abrirlo; «Usar este insumo» empieza deshabilitado", async () => {
    await irAApu();
    const boton = screen.getByRole("button", { name: "Cambiar el insumo de una línea (en la copia de esta versión)" });
    expect(boton).toHaveAttribute("aria-expanded", "false");
    expect(urlsDeInsumos()).toHaveLength(0);
    await userEvent.click(boton);
    expect(boton).toHaveAttribute("aria-expanded", "true");
    await screen.findByRole("option", { name: /MAT-010/ });
    expect(urlsDeInsumos()).toEqual([`/v1/hoja/borradores/${ID}/insumos?tipo=material&limite=301`]);
    expect(screen.getByRole("button", { name: "Usar este insumo" })).toBeDisabled();
  });

  test("3c-F11 (E7): elegir tipo, línea e insumo y pulsar «Usar este insumo» manda rev, tipo, índice desde 0 y código; se relee y se avisa", async () => {
    await irAApu();
    await abrirInsumo();
    await screen.findByRole("option", { name: /MAT-010/ });
    // Los candidatos muestran código, descripción, unidad y precio.
    expect(screen.getByRole("option", { name: "MAT-010 · Llave de bola PVC 3/4 · pieza · 8,10" })).toBeInTheDocument();
    const u = userEvent.setup({ delay: null });
    await u.selectOptions(screen.getByRole("combobox", { name: "Insumo" }), "MAT-010");
    expect(screen.getByRole("button", { name: "Usar este insumo" })).toBeEnabled();
    const lecturas = lecturasDeApu();
    await u.click(screen.getByRole("button", { name: "Usar este insumo" }));
    await esperar(() => expect(escriturasDeInsumo()).toEqual([{ rev: 0, tipo: "material", indice: 0, insumo: "MAT-010" }]));
    expect(llamadasA("POST", /\/apu\/AF-LLAVE\/insumo$/)).toHaveLength(1);
    await esperar(() => expect(lecturasDeApu()).toBeGreaterThan(lecturas));
    expect(await screen.findByText("Insumo de la línea 1 cambiado: Llave de bola PVC 3/4.")).toBeInTheDocument();
    await esperar(() => within(regionDeEstado()).getByText(/· 1 cambio sin guardar/));
    // La elección se limpia: hay que elegir otro insumo para volver a cambiar.
    expect(screen.getByRole("button", { name: "Usar este insumo" })).toBeDisabled();
  });

  test("al cambiar el tipo de línea se piden los candidatos de ese tipo y la línea se elige entre las de ese rubro", async () => {
    await irAApu();
    await abrirInsumo();
    await screen.findByRole("option", { name: /MAT-010/ });
    candidatos = (url) =>
      url.searchParams.get("tipo") === "mano_obra"
        ? { insumos: [insumo("MO-007", "Plomero de 2da N4", "jornal", "1.95")], hay_mas: false }
        : MATERIALES;
    const u = userEvent.setup({ delay: null });
    await u.selectOptions(screen.getByRole("combobox", { name: "Tipo de línea" }), "mano_obra");
    await screen.findByRole("option", { name: /MO-007/ });
    expect(urlsDeInsumos().at(-1)).toBe(`/v1/hoja/borradores/${ID}/insumos?tipo=mano_obra&limite=301`);
    const lineas = within(screen.getByRole("combobox", { name: "Línea" })).getAllByRole("option");
    expect(lineas.map((o) => o.textContent)).toEqual(["1. Plomero de 1ra N5", "2. Ayudante N2"]);
    await u.selectOptions(screen.getByRole("combobox", { name: "Línea" }), "1");
    await u.selectOptions(screen.getByRole("combobox", { name: "Insumo" }), "MO-007");
    await u.click(screen.getByRole("button", { name: "Usar este insumo" }));
    await esperar(() => expect(escriturasDeInsumo()).toEqual([{ rev: 0, tipo: "mano_obra", indice: 1, insumo: "MO-007" }]));
  });

  test("un rubro sin líneas lo dice y no ofrece candidatos", async () => {
    apu = vistaApu({ detalle: detalleDeCodo(), seleccionada: "AF-CODO-1/2" });
    await irAApu();
    await abrirInsumo();
    const u = userEvent.setup({ delay: null });
    await u.selectOptions(screen.getByRole("combobox", { name: "Tipo de línea" }), "equipo");
    expect(await screen.findByText("Este APU no tiene líneas de ese tipo.")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Insumo" })).toBeNull();
  });

  test("buscar por descripción acota los candidatos (pausa de 300 ms) y sin coincidencias lo dice", async () => {
    await irAApu();
    await abrirInsumo();
    await screen.findByRole("option", { name: /MAT-010/ });
    relojFalso();
    candidatos = () => ({ insumos: [], hay_mas: false });
    fireEvent.change(screen.getByRole("textbox", { name: "Buscar insumo (código o descripción)" }), { target: { value: " zzz " } });
    await pausa(299);
    expect(urlsDeInsumos()).toHaveLength(1);
    await pausa(1);
    await esperar(() => expect(urlsDeInsumos().at(-1)).toBe(`/v1/hoja/borradores/${ID}/insumos?tipo=material&texto=zzz&limite=301`));
    expect(await esperar(() => screen.getByText("Ningún insumo de la lista coincide: pruebe con otra palabra."))).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Insumo" })).toBeNull();
  });

  test("con más de 300 candidatos se muestran 300 y se pide acotar por descripción (como la clásica)", async () => {
    candidatos = () => ({
      insumos: Array.from({ length: 301 }, (_, i) => insumo(`MAT-${1000 + i}`, `Insumo ${1000 + i}`, "u", "1.00")),
      hay_mas: true,
    });
    await irAApu();
    await abrirInsumo();
    await screen.findByText("Hay más de 300 insumos: escriba parte de la descripción para acotar.");
    expect(within(screen.getByRole("combobox", { name: "Insumo" })).getAllByRole("option")).toHaveLength(301); // 300 y el marcador
  });

  test("sin versión abierta los insumos no se eligen: se dice por qué y no se piden candidatos", async () => {
    abierto = borrador({}, false);
    apu = vistaApu({ detalle: { ...vistaApu().detalle!, solo_lectura_insumos: true } });
    await irAApu();
    await abrirInsumo();
    expect(screen.getByText("Abra una versión guardada: los insumos se eligen de su lista de precios.")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Insumo" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Usar este insumo" })).toBeNull();
    expect(urlsDeInsumos()).toHaveLength(0);
  });

  test("un 422 del cambio de insumo (fuera de la lista) se muestra verbatim, sin la frase del APU, y la elección se conserva", async () => {
    await irAApu();
    await abrirInsumo();
    await screen.findByRole("option", { name: /MAT-010/ });
    const DETALLE = "El insumo MAT-010 no está en la lista de precios de la versión.";
    alCambiarInsumo = () => json({ detalle: DETALLE }, 422);
    const u = userEvent.setup({ delay: null });
    await u.selectOptions(screen.getByRole("combobox", { name: "Insumo" }), "MAT-010");
    await u.click(screen.getByRole("button", { name: "Usar este insumo" }));
    const alerta = await esperar(() => aviso());
    expect(alerta).toHaveTextContent(DETALLE);
    expect(alerta.textContent).not.toContain("La hoja sigue con");
    expect(screen.getByRole("combobox", { name: "Insumo" })).toHaveValue("MAT-010");
  });

  test("un 409 de «versión no abierta» al cambiar el insumo se muestra tal cual, sin bloquear la edición", async () => {
    await irAApu();
    await abrirInsumo();
    await screen.findByRole("option", { name: /MAT-010/ });
    const DETALLE = "Abra una version guardada: los insumos se eligen de su lista de precios.";
    alCambiarInsumo = () => json({ detalle: DETALLE }, 409);
    const u = userEvent.setup({ delay: null });
    await u.selectOptions(screen.getByRole("combobox", { name: "Insumo" }), "MAT-010");
    await u.click(screen.getByRole("button", { name: "Usar este insumo" }));
    expect(await esperar(() => aviso())).toHaveTextContent(DETALLE);
    expect(screen.queryByRole("button", { name: "Recargar el borrador" })).toBeNull();
    relojFalso();
    fireEvent.change(campo("Cantidad, Equipos fila 1"), { target: { value: "2" } });
    await pausa(400);
    await esperar(() => expect(escriturasDeApu()).toHaveLength(1)); // la edición sigue disponible
  });

  test("«Usar este insumo» con una cantidad en la pausa: primero sale la edición y el cambio de insumo lleva el rev que contestó", async () => {
    await irAApu();
    await abrirInsumo();
    await screen.findByRole("option", { name: /MAT-010/ });
    const u = userEvent.setup({ delay: null });
    await u.selectOptions(screen.getByRole("combobox", { name: "Insumo" }), "MAT-010");
    relojFalso();
    fireEvent.change(campo("Cantidad, Materiales fila 1"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "Usar este insumo" }));
    await esperar(() => expect(escriturasDeInsumo()).toHaveLength(1));
    expect(escriturasDeApu()).toHaveLength(1);
    expect(escriturasDeApu()[0]!.rev).toBe(0);
    expect(escriturasDeInsumo()[0]!.rev).toBe(1);
    const orden = fetchFalso.mock.calls.filter(([, i]) => i?.method === "PUT" || i?.method === "POST").map(([r]) => decodeURIComponent(String(r)));
    expect(orden.indexOf(`/v1/hoja/borradores/${ID}/apu/AF-LLAVE`)).toBeLessThan(orden.indexOf(`/v1/hoja/borradores/${ID}/apu/AF-LLAVE/insumo`));
  });

  test("el cambio de insumo conserva lo escrito en las cantidades del editor", async () => {
    await irAApu();
    await abrirInsumo();
    await screen.findByRole("option", { name: /MAT-010/ });
    const u = userEvent.setup({ delay: null });
    await u.selectOptions(screen.getByRole("combobox", { name: "Insumo" }), "MAT-010");
    await u.type(campo("Cantidad, Equipos fila 1"), "5");
    expect(campo("Cantidad, Equipos fila 1")).toHaveValue("15");
    await u.click(screen.getByRole("button", { name: "Usar este insumo" }));
    await esperar(() => expect(escriturasDeInsumo()).toHaveLength(1));
    await screen.findByText("Insumo de la línea 1 cambiado: Llave de bola PVC 3/4.");
    expect(campo("Cantidad, Equipos fila 1")).toHaveValue("15");
  });

  // --- Secretos y estática ------------------------------------------------------------------------------------------------

  test("editar el APU no deja nada en localStorage ni sessionStorage", async () => {
    await irAApu();
    relojFalso();
    fireEvent.change(campo("Cantidad, Equipos fila 1"), { target: { value: "secreto-no-guardar" } });
    await pausa(400);
    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  test("3c-F13: los archivos del APU están bajo la prueba estática (sin Number, parseFloat, toFixed ni + unario)", () => {
    const fuentes = import.meta.glob("./*.{ts,tsx}", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
    for (const ruta of ["./logicaApu.ts", "./logicaRetomar.ts", "./PestanaApu.tsx", "./CambioDeInsumo.tsx"]) {
      expect(Object.keys(fuentes), ruta).toContain(ruta);
      expect(fuentes[ruta], ruta).not.toMatch(
        /\bNumber\s*\(|\bparseFloat\s*\(|\bparseInt\s*\(|\.toFixed\s*\(|(?:[=(,:?]|\breturn)\s*\+\s*[A-Za-z_$(]/,
      );
    }
  });
});
