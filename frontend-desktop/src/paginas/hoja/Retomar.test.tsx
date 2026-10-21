import { act, configure, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { informeAuditoria, vistaEspacio, vistaParametros } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, Resumen, VersionesRespuesta } from "./logica";

// Rebanada 3c-3: retomar el borrador tras recargar o volver a la página (E10, E11; 3c-F16) y cambiar de versión con un
// borrador abierto (3c-F9, P23). El servidor se simula con respuestas ficticias con la forma del contrato (diseño §4.4):
// E10 `GET /v1/hoja/borradores` -> `[{id, proyecto, version, cambios, tocado}]`; E11 `POST /v1/hoja/borradores` -> 409
// `{detalle, borrador_id}` si ya hay uno con cambios de esa versión; R3 `GET …/{id}`; R4 `DELETE …/{id}` -> 204. Caso
// ficticio OF-001; los literales son de su memoria y del diseño.
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
const OTRO = "id-borrador-bbbbbbbbbbbb";
const FALTA =
  "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). Lo que no guardó se perdió: abra la versión otra vez.";
const VERSIONES: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "002",
  versiones: [
    { codigo: "002", fecha: "2026-10-06", motivo: "edicion", origen: "001", vigente: true, descartada: false, cambios: 1 },
    { codigo: "001", fecha: "2026-10-05", motivo: "", origen: "", vigente: false, descartada: false, cambios: 0 },
  ],
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

function borrador(version: string | null = "002", extra: Partial<Resumen> = {}, id = ID): BorradorAbierto {
  return {
    id,
    base: { proyecto: "OF-001", version, vigente: "002", lista: "Lista", espacio_de: version, solo_lectura: false, moneda: "USD" },
    resumen: resumen(extra),
    instantanea: { creadas: 0, mensaje: null },
  };
}

const guardado = (extra: Record<string, unknown> = {}) => ({
  id: ID,
  proyecto: "OF-001",
  version: "002",
  cambios: 2,
  rev: 3,
  tocado: "2026-10-20T10:00:00",
  ...extra,
});

describe("Hoja del proyecto: retomar el borrador y cambiar de versión (3c-3)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  // Lo que el servidor simulado contesta; cada prueba lo cambia.
  let lista: () => Response;
  let alAbrir: (cuerpo: { proyecto: string; version: string | null; reemplazar?: boolean }) => Response;
  let alVivo: (id: string) => Response;
  let alBorrar: (id: string) => Response | Promise<Response>;
  let alPonerParametros: (cuerpo: { rev: number }) => Response;
  let borradorDeVersion: (version: string | null) => BorradorAbierto;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    localStorage.clear();
    sessionStorage.clear();
    borradorDeVersion = (v) => borrador(v);
    lista = () => json({ borradores: [] });
    alAbrir = (c) => json(borradorDeVersion(c.version), 201);
    alVivo = (id) => {
      const b = borradorDeVersion("002");
      return json({ id, base: b.base, resumen: b.resumen });
    };
    alBorrar = () => new Response(null, { status: 204 });
    alPonerParametros = (c) => json({ rev: c.rev + 1, resumen: resumen({ rev: c.rev + 1, cambios: 1 }) });
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = new URL(String(ruta), "http://silice.local");
      const metodo = init?.method ?? "GET";
      const camino = url.pathname;
      if (camino === "/v1/hoja/versiones") return json(VERSIONES);
      if (camino === "/v1/hoja/borradores" && metodo === "GET") return lista();
      if (camino === "/v1/hoja/borradores" && metodo === "POST") return alAbrir(JSON.parse(String(init?.body)));
      const propio = /^\/v1\/hoja\/borradores\/([^/]+)$/.exec(camino);
      if (propio && metodo === "GET") return alVivo(propio[1]!);
      if (propio && metodo === "DELETE") return alBorrar(propio[1]!);
      if (camino.endsWith("/parametros") && metodo === "PUT") return alPonerParametros(JSON.parse(String(init?.body)));
      if (camino.endsWith("/vistas/espacio")) return json(vistaEspacio());
      if (camino.endsWith("/vistas/parametros")) return json(vistaParametros());
      if (camino.endsWith("/vistas/auditoria")) return json(informeAuditoria());
      return new Response(null, { status: 204 });
    });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  const llamadas = (metodo: string, url: string) =>
    fetchFalso.mock.calls.filter(([r, init]) => String(r) === url && (init?.method ?? "GET") === metodo);
  const aperturas = () => llamadas("POST", "/v1/hoja/borradores").map(([, i]) => JSON.parse(String(i?.body)) as { version: string | null });
  const borrados = (id = ID) => llamadas("DELETE", `/v1/hoja/borradores/${id}`);
  const orden = () => fetchFalso.mock.calls.map(([r, i]) => `${i?.method ?? "GET"} ${String(r)}`);

  let proyectoActual = "OF-001";
  let nombreActual: string | null = null;
  function valor(): Aplicacion {
    return {
      sesion: SESION,
      proyecto: proyectoActual,
      nombreProyecto: nombreActual,
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
  }
  function montar() {
    const r = render(
      <ContextoAplicacion.Provider value={valor()}>
        <PaginaHoja />
      </ContextoAplicacion.Provider>,
    );
    return {
      ...r,
      conProyecto: (proyecto: string) => {
        proyectoActual = proyecto;
        r.rerender(
          <ContextoAplicacion.Provider value={valor()}>
            <PaginaHoja />
          </ContextoAplicacion.Provider>,
        );
      },
    };
  }
  beforeEach(() => {
    proyectoActual = "OF-001";
    nombreActual = null;
  });

  const estado = () => screen.getByRole("region", { name: "Estado del borrador" });
  const pausa = (ms: number) =>
    act(async () => {
      vi.advanceTimersByTime(ms);
    });
  const relojFalso = () => vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  const saleLaPagina = () => {
    const evento = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(evento);
    return evento.defaultPrevented;
  };
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
  // Da turnos a las promesas y comprueba que algo NO ocurre.
  async function nuncaOcurre(comprobar: () => boolean) {
    for (let i = 0; i < 40; i++) {
      await act(async () => {
        await new Promise<void>((resolver) => setImmediate(resolver));
      });
      expect(comprobar()).toBe(false);
    }
  }

  // --- Retomar (E10, E11; 3c-F16) ---------------------------------------------------------------------------------------

  test("sin borradores guardados, la hoja abre uno nuevo como siempre; la lista se pide antes de abrir", async () => {
    montar();
    await screen.findByRole("region", { name: "Estado del borrador" });
    expect(aperturas()).toEqual([{ proyecto: "OF-001", version: "002" }]);
    const o = orden();
    expect(o.indexOf("GET /v1/hoja/borradores")).toBeGreaterThanOrEqual(0);
    expect(o.indexOf("GET /v1/hoja/borradores")).toBeLessThan(o.indexOf("POST /v1/hoja/borradores"));
    expect(screen.queryByRole("button", { name: /Retomar borrador/ })).toBeNull();
  });

  test("el servidor lista el borrador con el NOMBRE del proyecto y la cabecera tiene su código: igual se ofrece retomarlo", async () => {
    const nombre = "OF-001: oficina con baño, cocineta y puestos (caso de prueba)";
    nombreActual = nombre;
    lista = () => json({ borradores: [guardado({ proyecto: nombre })] });
    montar();
    // el rótulo dice el nombre del proyecto (el código puede ser un número interno que nadie reconoce)
    expect(await screen.findByRole("button", { name: `Retomar borrador de ${nombre} (2 cambios)` })).toBeInTheDocument();
    expect(aperturas()).toEqual([]); // nada se abre hasta que la persona decida
  });

  test("con un borrador con cambios se ofrece «Retomar borrador de OF-001 (2 cambios)» y no se abre otro hasta decidir", async () => {
    lista = () => json({ borradores: [guardado()] });
    montar();
    const retomar = await screen.findByRole("button", { name: "Retomar borrador de OF-001 (2 cambios)" });
    expect(retomar).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Descartar y abrir de nuevo" })).toBeInTheDocument();
    await nuncaOcurre(() => aperturas().length > 0);
    expect(screen.queryByRole("region", { name: "Estado del borrador" })).toBeNull();
  });

  test("Retomar: lee el borrador vivo, muestra sus cambios y su total, rehidrata las tablas del servidor y sigue desde su rev", async () => {
    lista = () => json({ borradores: [guardado()] });
    alVivo = (id) => {
      const b = borrador("002", { rev: 4, cambios: 2, total: m("2800.50", "2800.5") });
      return json({ id, base: b.base, resumen: b.resumen });
    };
    montar();
    fireEvent.click(await screen.findByRole("button", { name: "Retomar borrador de OF-001 (2 cambios)" }));
    await screen.findByRole("region", { name: "Estado del borrador" });
    expect(llamadas("GET", `/v1/hoja/borradores/${ID}`)).toHaveLength(1);
    expect(aperturas()).toHaveLength(0); // se retoma, no se abre otro
    expect(within(estado()).getByText(/Versión 002 · 2 cambios sin guardar/)).toBeInTheDocument();
    expect(within(estado()).getByTitle("2800.5")).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Versión" })).toHaveValue("002");
    expect(saleLaPagina()).toBe(true); // hay cambios sin guardar
    expect(screen.queryByRole("button", { name: /Retomar borrador/ })).toBeNull();
    // Las tablas salen del borrador del servidor (no de la versión guardada).
    expect(await screen.findByRole("textbox", { name: "Largo (m), Ambientes fila 1" })).toHaveValue("2");
    // Y la siguiente edición lleva el rev con que quedó el borrador.
    await userEvent.click(screen.getByRole("tab", { name: "Parámetros" }));
    const campo = await screen.findByRole("textbox", { name: /^Administración/ });
    const cuerpos: Array<{ rev: number }> = [];
    alPonerParametros = (c) => {
      cuerpos.push(c);
      return json({ rev: c.rev + 1, resumen: resumen({ rev: c.rev + 1, cambios: 3 }) });
    };
    relojFalso();
    fireEvent.change(campo, { target: { value: "0.20" } });
    await pausa(400);
    await esperar(() => expect(cuerpos).toHaveLength(1));
    expect(cuerpos[0]!.rev).toBe(4);
  });

  test("«Descartar y abrir de nuevo» borra el borrador ofrecido y abre uno nuevo de la versión", async () => {
    lista = () => json({ borradores: [guardado()] });
    montar();
    fireEvent.click(await screen.findByRole("button", { name: "Descartar y abrir de nuevo" }));
    await screen.findByRole("region", { name: "Estado del borrador" });
    expect(borrados()).toHaveLength(1);
    expect(aperturas()).toEqual([{ proyecto: "OF-001", version: "002" }]);
    const o = orden();
    expect(o.indexOf(`DELETE /v1/hoja/borradores/${ID}`)).toBeLessThan(o.indexOf("POST /v1/hoja/borradores"));
    expect(within(estado()).getByText(/Sin cambios sin guardar/)).toBeInTheDocument();
  });

  test.each([
    ["de otro proyecto", [guardado({ proyecto: "TI-001" })]],
    ["sin cambios", [guardado({ cambios: 0 })]],
  ])("un borrador %s no se ofrece: se abre uno nuevo", async (_nombre, filas) => {
    lista = () => json({ borradores: filas });
    montar();
    await screen.findByRole("region", { name: "Estado del borrador" });
    expect(screen.queryByRole("button", { name: /Retomar borrador/ })).toBeNull();
    expect(aperturas()).toHaveLength(1);
  });

  test.each([
    ["un error del servidor", () => json({ detalle: "No se pudo leer el caso." }, 503)],
    ["algo que no es una lista", () => json({ otra: "cosa" })],
  ])("si la lista de borradores falla (%s), la hoja se abre igual", async (_nombre, respuesta) => {
    lista = respuesta;
    montar();
    await screen.findByRole("region", { name: "Estado del borrador" });
    expect(aperturas()).toHaveLength(1);
    // Carbon pone en cada campo un `role="alert"` vacío (su contador): los avisos de verdad son los que traen texto.
    expect(screen.queryAllByRole("alert").filter((a) => (a.textContent ?? "") !== "")).toHaveLength(0);
  });

  test("un 401 al pedir la lista avisa al marco para que pida la sesión de nuevo", async () => {
    lista = () => json({ detalle: "Inicie sesión." }, 401);
    montar();
    await esperar(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("con varios borradores del proyecto, cada botón dice su versión y retoma el suyo", async () => {
    lista = () => json({ borradores: [guardado(), guardado({ id: OTRO, version: "001", cambios: 1 })] });
    alVivo = (id) => {
      const b = borrador(id === OTRO ? "001" : "002", { cambios: 1 }, id);
      return json({ id, base: b.base, resumen: b.resumen });
    };
    montar();
    expect(await screen.findByRole("button", { name: "Retomar borrador de OF-001, versión 002 (2 cambios)" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retomar borrador de OF-001, versión 001 (1 cambio)" }));
    await screen.findByRole("region", { name: "Estado del borrador" });
    expect(llamadas("GET", `/v1/hoja/borradores/${OTRO}`)).toHaveLength(1);
    expect(screen.getByRole("combobox", { name: "Versión" })).toHaveValue("001");
    expect(within(estado()).getByText(/Versión 001 · 1 cambio sin guardar/)).toBeInTheDocument();
  });

  test("retomar un borrador que el servidor ya no tiene: lo dice y «Abrir de nuevo» abre uno nuevo sin volver a ofrecer", async () => {
    lista = () => json({ borradores: [guardado()] });
    alVivo = () => json({ detalle: FALTA }, 404);
    montar();
    fireEvent.click(await screen.findByRole("button", { name: "Retomar borrador de OF-001 (2 cambios)" }));
    expect(await screen.findByText("El borrador ya no está")).toBeInTheDocument();
    expect(aperturas()).toHaveLength(0);
    fireEvent.click(screen.getByRole("button", { name: "Abrir de nuevo" }));
    await screen.findByRole("region", { name: "Estado del borrador" });
    expect(aperturas()).toEqual([{ proyecto: "OF-001", version: "002" }]);
    expect(screen.queryByRole("button", { name: /Retomar borrador/ })).toBeNull();
  });

  test("E11: si al abrir el servidor contesta 409 con el borrador existente, se ofrece retomarlo en vez de mostrar un error", async () => {
    let pedidas = 0;
    lista = () => (pedidas++ === 0 ? json({ borradores: [] }) : json({ borradores: [guardado()] }));
    alAbrir = () =>
      json({ detalle: "Ya hay un borrador de esa versión con cambios sin guardar.", borrador_id: ID }, 409);
    montar();
    expect(await screen.findByRole("button", { name: "Retomar borrador de OF-001 (2 cambios)" })).toBeInTheDocument();
    expect(screen.queryAllByRole("alert").filter((a) => (a.textContent ?? "") !== "")).toHaveLength(0);
    expect(aperturas()).toHaveLength(1); // no vuelve a intentarlo solo
  });

  test("3c-F16: con 2 cambios, salir de la página no borra el borrador; al volver se ofrece retomarlo", async () => {
    borradorDeVersion = (v) => borrador(v, { cambios: 2, rev: 3 });
    const primera = montar();
    await screen.findByText(/· 2 cambios sin guardar/);
    primera.unmount();
    await nuncaOcurre(() => borrados().length > 0);
    lista = () => json({ borradores: [guardado()] });
    montar();
    expect(await screen.findByRole("button", { name: "Retomar borrador de OF-001 (2 cambios)" })).toBeInTheDocument();
  });

  test("3c-F16: sin cambios, salir de la página sí borra el borrador", async () => {
    const primera = montar();
    await screen.findByText(/Sin cambios sin guardar/);
    primera.unmount();
    await esperar(() => expect(borrados()).toHaveLength(1));
  });

  test("3c-F16: cambiar de proyecto en la cabecera no pierde el borrador con cambios; al volver se ofrece retomarlo", async () => {
    borradorDeVersion = (v) => borrador(v, { cambios: 2, rev: 3 });
    const pagina = montar();
    await screen.findByText(/· 2 cambios sin guardar/);
    pagina.conProyecto("TI-001");
    await esperar(() => expect(aperturas()).toHaveLength(2)); // abrió el de TI-001
    expect(borrados()).toHaveLength(0);
    lista = () => json({ borradores: [guardado()] });
    pagina.conProyecto("OF-001");
    expect(await screen.findByRole("button", { name: "Retomar borrador de OF-001 (2 cambios)" })).toBeInTheDocument();
  });

  // --- Cambio de versión con un borrador abierto (3c-F9, P23) ------------------------------------------------------------

  async function abrirConCambios(cambios = 2) {
    borradorDeVersion = (v) => borrador(v, { cambios, rev: 3 });
    montar();
    await screen.findByText(new RegExp(`· ${cambios} cambio`));
  }
  const elegirVersion = (v: string) => fireEvent.change(screen.getByRole("combobox", { name: "Versión" }), { target: { value: v } });

  test("sin cambios, elegir otra versión la abre sin preguntar", async () => {
    montar();
    await screen.findByText(/Sin cambios sin guardar/);
    elegirVersion("001");
    await esperar(() => expect(aperturas()).toHaveLength(2));
    expect(aperturas()[1]).toEqual({ proyecto: "OF-001", version: "001" });
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  test("3c-F9: con cambios, elegir otra versión abre un diálogo que lleva el foco, bloquea el resto y no abre nada todavía", async () => {
    await abrirConCambios(2);
    elegirVersion("001");
    const dialogo = await screen.findByRole("alertdialog");
    expect(dialogo).toHaveAttribute("aria-modal", "true");
    expect(dialogo).toHaveFocus();
    expect(within(dialogo).getByText("Tiene 2 cambios sin guardar. Si abre otra versión se pierden: guarde primero o descarte.")).toBeInTheDocument();
    expect(within(dialogo).getByRole("heading", { name: "Descartar los cambios" })).toBeInTheDocument();
    expect(within(dialogo).getByRole("button", { name: "Descartar y abrir" })).toBeInTheDocument();
    expect(within(dialogo).getByRole("button", { name: "Seguir editando" })).toBeInTheDocument();
    // El resto de la página queda inerte mientras el diálogo está abierto.
    expect(screen.getByRole("combobox", { name: "Versión", hidden: true }).closest("[inert]")).not.toBeNull();
    expect(dialogo.closest("[inert]")).toBeNull();
    expect(aperturas()).toHaveLength(1);
    expect(borrados()).toHaveLength(0);
    // Con un solo cambio el texto va en singular.
  });

  test("el texto del diálogo con un solo cambio va en singular", async () => {
    await abrirConCambios(1);
    elegirVersion("001");
    const dialogo = await screen.findByRole("alertdialog");
    expect(within(dialogo).getByText("Tiene 1 cambio sin guardar. Si abre otra versión se pierden: guarde primero o descarte.")).toBeInTheDocument();
  });

  test("«Seguir editando» cierra el diálogo, deja la versión que estaba y no borra ni abre nada; el foco vuelve al selector", async () => {
    await abrirConCambios(2);
    elegirVersion("001");
    fireEvent.click(await screen.findByRole("button", { name: "Seguir editando" }));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(screen.getByRole("combobox", { name: "Versión" })).toHaveValue("002");
    expect(screen.getByRole("combobox", { name: "Versión" })).toHaveFocus();
    expect(aperturas()).toHaveLength(1);
    expect(borrados()).toHaveLength(0);
    expect(within(estado()).getByText(/· 2 cambios sin guardar/)).toBeInTheDocument();
  });

  test.each([
    ["Seguir editando", async () => fireEvent.click(await screen.findByRole("button", { name: "Seguir editando" }))],
    ["Esc", async () => userEvent.keyboard("{Escape}")],
    ["Descartar y abrir", async () => fireEvent.click(await screen.findByRole("button", { name: "Descartar y abrir" }))],
  ])("el foco vuelve al selector DESPUÉS de quitar el inert (%s): un navegador real no enfoca dentro de un subárbol inert", async (_n, cerrar) => {
    await abrirConCambios(2);
    elegirVersion("001");
    await screen.findByRole("alertdialog");
    const enfocados: Array<{ id: string; inerte: boolean }> = [];
    const original = HTMLElement.prototype.focus;
    HTMLElement.prototype.focus = function (this: HTMLElement, ...args: Parameters<HTMLElement["focus"]>) {
      if (this.id === "hoja-version") enfocados.push({ id: this.id, inerte: this.closest("[inert]") !== null });
      return original.apply(this, args);
    };
    try {
      await cerrar();
      await esperar(() => expect(enfocados.length).toBeGreaterThan(0));
      expect(enfocados.every((e) => !e.inerte)).toBe(true);
    } finally {
      HTMLElement.prototype.focus = original;
    }
  });

  test("Esc equivale a «Seguir editando»", async () => {
    await abrirConCambios(2);
    elegirVersion("001");
    await screen.findByRole("alertdialog");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(screen.getByRole("combobox", { name: "Versión" })).toHaveValue("002");
    expect(borrados()).toHaveLength(0);
  });

  test("Tab no sale del diálogo: del último botón vuelve al primero y Mayús+Tab hace lo inverso", async () => {
    await abrirConCambios(2);
    elegirVersion("001");
    const dialogo = await screen.findByRole("alertdialog");
    const u = userEvent.setup({ delay: null });
    const confirmar = within(dialogo).getByRole("button", { name: "Descartar y abrir" });
    const seguir = within(dialogo).getByRole("button", { name: "Seguir editando" });
    seguir.focus();
    await u.tab();
    expect(confirmar).toHaveFocus();
    await u.tab({ shift: true });
    expect(seguir).toHaveFocus();
  });

  test("P23: «Descartar y abrir» borra el borrador, abre la versión elegida y cierra el diálogo; nada se descarta antes", async () => {
    await abrirConCambios(2);
    elegirVersion("001");
    fireEvent.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Descartar y abrir" }));
    await esperar(() => expect(aperturas()).toHaveLength(2));
    expect(aperturas()[1]).toEqual({ proyecto: "OF-001", version: "001" });
    expect(borrados()).toHaveLength(1); // una sola vez: el de la limpieza no lo repite
    const o = orden();
    expect(o.indexOf(`DELETE /v1/hoja/borradores/${ID}`)).toBeLessThan(o.lastIndexOf("POST /v1/hoja/borradores"));
    await esperar(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(screen.getByRole("combobox", { name: "Versión" })).toHaveValue("001");
  });

  test("si el servidor no puede borrar el borrador, no se abre la otra versión y se dice por qué", async () => {
    await abrirConCambios(2);
    alBorrar = () => json({ detalle: "No se pudo leer o escribir el caso." }, 503);
    elegirVersion("001");
    fireEvent.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Descartar y abrir" }));
    expect(await screen.findByText("No se pudo leer o escribir el caso.")).toBeInTheDocument();
    expect(aperturas()).toHaveLength(1);
  });

  // --- Borde de 3c-1: salir de la página dentro de los 400 ms de una edición -----------------------------------------------

  async function editarParametroYSalir(respuesta: (c: { rev: number }) => Response) {
    alPonerParametros = respuesta;
    const pagina = montar();
    await screen.findByText(/Sin cambios sin guardar/);
    await userEvent.click(screen.getByRole("tab", { name: "Parámetros" }));
    const campo = await screen.findByRole("textbox", { name: /^Administración/ });
    relojFalso();
    fireEvent.change(campo, { target: { value: "0.20" } });
    await pausa(100); // dentro de los 400 ms de la pausa
    pagina.unmount();
    await esperar(() => expect(llamadas("PUT", `/v1/hoja/borradores/${ID}/parametros`)).toHaveLength(1));
  }

  test("si se sale dentro de la pausa y el servidor acepta la edición, el borrador queda (tiene cambios) y no se borra", async () => {
    await editarParametroYSalir((c) => json({ rev: c.rev + 1, resumen: resumen({ rev: c.rev + 1, cambios: 1 }) }));
    await nuncaOcurre(() => borrados().length > 0);
  });

  test.each([
    ["el valor deja el borrador igual", (c: { rev: number }) => json({ rev: c.rev, resumen: resumen({ rev: c.rev, cambios: 0 }) })],
    ["el servidor rechaza el valor", () => json({ detalle: "parametros: administracion: 'x' no es un numero decimal valido" }, 422)],
  ])("si se sale dentro de la pausa y %s (sin cambios), el borrador se borra pero DESPUÉS de que termine la edición", async (_nombre, respuesta) => {
    let terminar: () => void = () => undefined;
    const puesta = new Promise<void>((resolver) => {
      terminar = resolver;
    });
    await editarParametroYSalir((c) => {
      void puesta;
      return respuesta(c);
    });
    await esperar(() => expect(borrados()).toHaveLength(1));
    const o = orden();
    expect(o.indexOf(`PUT /v1/hoja/borradores/${ID}/parametros`)).toBeLessThan(o.indexOf(`DELETE /v1/hoja/borradores/${ID}`));
    terminar();
  });

  test("el DELETE espera a que termine una edición que sigue en vuelo al salir", async () => {
    let contestar: (r: Response) => void = () => undefined;
    const respuesta = new Promise<Response>((resolver) => {
      contestar = resolver;
    });
    const pagina = montar();
    await screen.findByText(/Sin cambios sin guardar/);
    await userEvent.click(screen.getByRole("tab", { name: "Parámetros" }));
    const campo = await screen.findByRole("textbox", { name: /^Administración/ });
    relojFalso();
    fetchFalso.mockImplementation(
      ((impl) =>
        async (...args: Parameters<typeof fetch>) =>
          String(args[0]).endsWith("/parametros") && args[1]?.method === "PUT" ? respuesta : impl(...args))(fetchFalso.getMockImplementation()!),
    );
    fireEvent.change(campo, { target: { value: "0.20" } });
    await pausa(100);
    pagina.unmount();
    await esperar(() => expect(llamadas("PUT", `/v1/hoja/borradores/${ID}/parametros`)).toHaveLength(1));
    await nuncaOcurre(() => borrados().length > 0); // el PUT no ha terminado: el DELETE no sale
    await act(async () => contestar(json({ rev: 1, resumen: resumen({ rev: 1, cambios: 0 }) })));
    await esperar(() => expect(borrados()).toHaveLength(1));
  });

  // --- Estática -------------------------------------------------------------------------------------------------------------

  test("3c-F13: los archivos de retomar están bajo la prueba estática (sin Number, parseFloat, toFixed ni + unario)", () => {
    const fuentes = import.meta.glob("./*.{ts,tsx}", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
    for (const ruta of ["./index.tsx", "./useBorrador.ts", "./logicaRetomar.ts", "./OfertaDeRetomar.tsx", "./DialogoDeVersion.tsx", "./envioPendiente.ts"]) {
      expect(Object.keys(fuentes), ruta).toContain(ruta);
      expect(fuentes[ruta], ruta).not.toMatch(
        /\bNumber\s*\(|\bparseFloat\s*\(|\bparseInt\s*\(|\.toFixed\s*\(|(?:[=(,:?]|\breturn)\s*\+\s*[A-Za-z_$(]/,
      );
    }
  });
});
