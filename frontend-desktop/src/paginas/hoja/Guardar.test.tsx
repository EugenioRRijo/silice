import { act, configure, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { informeAuditoria, vistaEspacio, vistaParametros } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, Resumen, VersionesRespuesta } from "./logica";

// Rebanada 3d-1 (front): el modal «Guardar versión», la primera versión y la reacción a cada resultado de S1
// (`POST /v1/hoja/borradores/{id}/guardar`, contrato `2026-10-20-hoja-3d1-contrato-rutas.md`) y de E9 (`…/cambios`). El servidor se
// simula con respuestas ficticias con la forma del contrato. Caso ficticio OF-001 (cifras de su memoria: total 2 703,86 USD); los
// literales de los mensajes están escritos a mano desde el contrato y la clásica.
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
const m = (texto: string, exacto = texto) => ({ texto, exacto });
const fila = (codigo: string, vigente: boolean, origen = "") => ({
  codigo,
  fecha: "2026-10-06",
  motivo: "",
  origen,
  vigente,
  descartada: false,
  cambios: 0,
});
const VERSIONES: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "USD",
  por_omision: "002",
  versiones: [fila("002", true, "001"), fila("001", false)],
};
const VERSIONES_CON_003: VersionesRespuesta = {
  ...VERSIONES,
  por_omision: "003",
  versiones: [fila("003", true, "002"), ...VERSIONES.versiones.map((v) => ({ ...v, vigente: false }))],
};
const SIN_VERSIONES: VersionesRespuesta = { proyecto: "NU-001", moneda: "USD", por_omision: null, versiones: [] };

const CAMBIOS = [
  { objeto: "cantidad", clave: "AF-LLAVE|esp_puntos:P1", campo: "cantidad", antes: "3", despues: "5" },
  { objeto: "parametro", clave: "administracion", campo: "valor", antes: "0.15", despues: "0.20" },
];

function resumen(extra: Partial<Resumen> = {}): Resumen {
  return {
    rev: 3,
    moneda: "USD",
    total: m("2703.86", "2703.860232344044033333333333"),
    cambios: 2,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
    ...extra,
  };
}

function borrador(version: string | null, extra: Partial<Resumen> = {}, proyecto = "OF-001", soloLectura = false): BorradorAbierto {
  return {
    id: ID,
    base: { proyecto, version, vigente: version, lista: "Lista", espacio_de: version, solo_lectura: soloLectura, moneda: "USD" },
    resumen: resumen(extra),
    instantanea: { creadas: 0, mensaje: null },
  };
}

const FUENTE = "Acta de obra 12 del 2026-10-18";
const MAS_NUEVA =
  "Otra persona guardó la versión 004 después de que usted abrió la 002. Si guarda, su versión saldrá de la 002 y quedará como vigente sin lo de la 004.";
const FALTA =
  "Ese borrador ya no está en el servidor (se reinició Sílice, venció o se descartó). Lo que no guardó se perdió: abra la versión otra vez.";

describe("Hoja del proyecto: guardar versión y primera versión (3d-1)", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  let versiones: VersionesRespuesta;
  let alAbrir: (cuerpo: { proyecto: string; version: string | null }) => BorradorAbierto;
  let alVivo: () => Response;
  let alCambios: () => Response;
  let alGuardar: (cuerpo: Record<string, unknown>) => Response | Promise<Response>;
  let proyectoActual = "OF-001";

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    proyectoActual = "OF-001";
    versiones = VERSIONES;
    alAbrir = (c) => (c.version === "002" ? borrador("002") : borrador(c.version, { cambios: 0, rev: 0 }, c.proyecto));
    alVivo = () => {
      const b = borrador("002");
      return json({ id: ID, base: b.base, resumen: b.resumen });
    };
    alCambios = () => json({ rev: 3, cambios: CAMBIOS });
    alGuardar = () => json({ codigo: "003", proyecto: "OF-001", cambios: 2, total: m("2703.86"), primera: false, mensaje: "x" });
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = new URL(String(ruta), "http://silice.local");
      const metodo = init?.method ?? "GET";
      const camino = url.pathname;
      if (camino === "/v1/hoja/versiones") return json(versiones);
      if (camino === "/v1/hoja/borradores" && metodo === "GET") return json({ borradores: [] });
      if (camino === "/v1/hoja/borradores" && metodo === "POST") {
        const c = JSON.parse(String(init?.body)) as { proyecto: string; version: string | null };
        return json(alAbrir(c), 201);
      }
      if (camino.endsWith("/cambios")) return alCambios();
      if (camino.endsWith("/guardar") && metodo === "POST") return alGuardar(JSON.parse(String(init?.body)));
      const propio = /^\/v1\/hoja\/borradores\/([^/]+)$/.exec(camino);
      if (propio && metodo === "GET") return alVivo();
      if (propio && metodo === "DELETE") return new Response(null, { status: 204 });
      if (camino.endsWith("/vistas/espacio")) return json(vistaEspacio());
      if (camino.endsWith("/vistas/parametros")) return json(vistaParametros());
      if (camino.endsWith("/vistas/auditoria")) return json(informeAuditoria());
      return new Response(null, { status: 204 });
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const llamadas = (metodo: string, termina: string) =>
    fetchFalso.mock.calls.filter(([r, init]) => String(r).endsWith(termina) && (init?.method ?? "GET") === metodo);
  const guardados = () => llamadas("POST", "/guardar").map(([, i]) => JSON.parse(String(i?.body)) as Record<string, unknown>);
  const aperturas = () => llamadas("POST", "/v1/hoja/borradores").map(([, i]) => JSON.parse(String(i?.body)) as { version: string | null });
  const borrados = () => llamadas("DELETE", `/v1/hoja/borradores/${ID}`);

  function valor(): Aplicacion {
    return {
      sesion: SESION,
      proyecto: proyectoActual,
      caso: { nombre: "obra", ruta_relativa: "data/obra.db" },
      recargarProyectos: vi.fn(),
      alExpirar,
    };
  }
  function montar() {
    return render(
      <ContextoAplicacion.Provider value={valor()}>
        <PaginaHoja />
      </ContextoAplicacion.Provider>,
    );
  }
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

  const abrirModal = async (nombre = "Guardar versión…") => {
    fireEvent.click(await screen.findByRole("button", { name: nombre }));
    return screen.findByRole("dialog");
  };
  const campoFuente = (dialogo: HTMLElement) => within(dialogo).getByRole("textbox", { name: /^Fuente/ });
  async function escribirFuente(dialogo: HTMLElement, texto = FUENTE) {
    fireEvent.change(campoFuente(dialogo), { target: { value: texto } });
  }
  const confirmar = (dialogo: HTMLElement, nombre = "Guardar versión") => within(dialogo).getByRole("button", { name: nombre });

  // --- 3d-F1: el modal ---------------------------------------------------------------------------------------------------

  test("el botón «Guardar versión…» solo aparece con cambios sin guardar", async () => {
    alAbrir = () => borrador("002", { cambios: 0 });
    montar();
    await screen.findByRole("region", { name: "Estado del borrador" });
    expect(screen.queryByRole("button", { name: /^Guardar/ })).toBeNull();
  });

  test("3d-F1: el modal es un diálogo con foco adentro (en la fuente), el resto inerte, su resumen y la lista de cambios (E9)", async () => {
    montar();
    const dialogo = await abrirModal();
    expect(dialogo).toHaveAttribute("aria-modal", "true");
    expect(within(dialogo).getByRole("heading", { name: "Guardar versión" })).toBeInTheDocument();
    expect(dialogo.contains(document.activeElement)).toBe(true);
    expect(campoFuente(dialogo)).toHaveFocus();
    expect(dialogo.closest("[inert]")).toBeNull();
    expect(screen.getByRole("combobox", { name: "Versión", hidden: true }).closest("[inert]")).not.toBeNull();
    // Resumen de lo que se guarda: cambios, de qué versión sale y el total (con el exacto accesible).
    expect(within(dialogo).getByText(/Se registrarán 2 cambios en una versión nueva \(sale de la 002\)/)).toBeInTheDocument();
    expect(within(dialogo).getByTitle("2703.860232344044033333333333")).toHaveTextContent("2.703,86 USD");
    // El responsable es la persona de la sesión, de solo lectura.
    expect(within(dialogo).getByText("Responsable: Ana Pérez <ana>")).toBeInTheDocument();
    expect(within(dialogo).queryByRole("textbox", { name: /Responsable/ })).toBeNull();
    // La lista de cambios, con sus cinco columnas.
    const tabla = await within(dialogo).findByRole("table", { name: "Cambios que se guardan" });
    for (const columna of ["Objeto", "Clave", "Campo", "Antes", "Después"]) {
      expect(within(tabla).getByRole("columnheader", { name: columna })).toBeInTheDocument();
    }
    const filas = within(tabla).getAllByRole("row").slice(1);
    expect(filas).toHaveLength(2);
    expect(within(filas[0]!).getAllByRole("cell").map((c) => c.textContent)).toEqual(["cantidad", "AF-LLAVE, Punto P1", "cantidad", "3", "5"]);
    expect(within(filas[1]!).getAllByRole("cell").map((c) => c.textContent)).toEqual(["parametro", "administracion", "valor", "0.15", "0.20"]);
    expect(llamadas("GET", `/v1/hoja/borradores/${ID}/cambios`)).toHaveLength(1);
  });

  test("3d-F1: sin fuente el botón «Guardar versión» queda deshabilitado y dice por qué; con fuente se habilita", async () => {
    montar();
    const dialogo = await abrirModal();
    const boton = confirmar(dialogo);
    expect(boton).toBeDisabled();
    expect(within(dialogo).getByText("Escriba la fuente del cambio: por qué se cambia y con qué respaldo.")).toBeInTheDocument();
    expect(boton).toHaveAccessibleDescription("Escriba la fuente del cambio: por qué se cambia y con qué respaldo.");
    await escribirFuente(dialogo, "   ");
    expect(boton).toBeDisabled(); // solo espacios no es una fuente
    await escribirFuente(dialogo);
    expect(boton).toBeEnabled();
    expect(within(dialogo).queryByText(/Escriba la fuente/)).toBeNull();
    expect(campoFuente(dialogo)).toHaveAttribute("maxlength", "300"); // el tope del contrato
  });

  test("3d-F1: la fuente se llama «Fuente del cambio (por qué y con qué respaldo)»", async () => {
    montar();
    const dialogo = await abrirModal();
    expect(within(dialogo).getByRole("textbox", { name: "Fuente del cambio (por qué y con qué respaldo)" })).toBeInTheDocument();
  });

  test("3d-F1: Tab no sale del diálogo y Mayús+Tab hace lo inverso", async () => {
    montar();
    const dialogo = await abrirModal();
    await escribirFuente(dialogo);
    const u = userEvent.setup({ delay: null });
    const guardar = confirmar(dialogo);
    guardar.focus();
    await u.tab();
    expect(campoFuente(dialogo)).toHaveFocus();
    await u.tab({ shift: true });
    expect(guardar).toHaveFocus();
  });

  test.each([
    ["Esc", async () => userEvent.keyboard("{Escape}")],
    ["Cancelar", async () => fireEvent.click(await screen.findByRole("button", { name: "Cancelar" }))],
  ])("3d-F1: %s cierra el diálogo sin guardar y el foco vuelve al botón DESPUÉS de quitar el inert", async (_n, cerrar) => {
    montar();
    await abrirModal();
    const enfocados: Array<{ inerte: boolean }> = [];
    const original = HTMLElement.prototype.focus;
    HTMLElement.prototype.focus = function (this: HTMLElement, ...args: Parameters<HTMLElement["focus"]>) {
      if (this.id === "hoja-guardar-version") enfocados.push({ inerte: this.closest("[inert]") !== null });
      return original.apply(this, args);
    };
    try {
      await cerrar();
      await esperar(() => expect(enfocados.length).toBeGreaterThan(0));
      expect(enfocados.every((e) => !e.inerte)).toBe(true);
    } finally {
      HTMLElement.prototype.focus = original;
    }
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByRole("button", { name: "Guardar versión…" })).toHaveFocus();
    expect(guardados()).toHaveLength(0);
  });

  test("la fuente escrita se conserva si se cierra el diálogo y se vuelve a abrir", async () => {
    montar();
    const dialogo = await abrirModal();
    await escribirFuente(dialogo);
    await userEvent.keyboard("{Escape}");
    const otra = await abrirModal();
    expect(campoFuente(otra)).toHaveValue(FUENTE);
  });

  test("si la lista de cambios no se puede leer, el diálogo lo dice y aun así se puede guardar", async () => {
    alCambios = () => json({ detalle: "No se pudo leer o escribir el caso." }, 503);
    montar();
    const dialogo = await abrirModal();
    expect(await within(dialogo).findByText("No se pudo leer la lista de cambios.")).toBeInTheDocument();
    await escribirFuente(dialogo);
    expect(confirmar(dialogo)).toBeEnabled();
  });

  test("una versión en solo lectura no se guarda: el botón está deshabilitado y dice por qué", async () => {
    alAbrir = () => borrador("002", {}, "OF-001", true);
    montar();
    const dialogo = await abrirModal();
    await escribirFuente(dialogo);
    expect(confirmar(dialogo)).toBeDisabled();
    expect(
      within(dialogo).getByText("Esta versión está en solo lectura: alguna partida ya no tiene composición vigente en el catálogo."),
    ).toBeInTheDocument();
  });

  // --- 3d-F2: éxito ------------------------------------------------------------------------------------------------------

  test("3d-F2: guardar manda rev y fuente (sin responsable), dice «Se guardó la versión 003 con 2 cambios registrados.» y abre la 003", async () => {
    montar();
    // El contexto no se pierde: la pestaña elegida sigue siendo la misma.
    await userEvent.click(await screen.findByRole("tab", { name: "Parámetros" }));
    const dialogo = await abrirModal();
    await escribirFuente(dialogo);
    versiones = VERSIONES_CON_003;
    alAbrir = (c) => borrador(c.version, { cambios: 0, rev: 0 });
    fireEvent.click(confirmar(dialogo));
    expect(await screen.findByText("Se guardó la versión 003 con 2 cambios registrados.")).toBeInTheDocument();
    expect(guardados()).toEqual([{ rev: 3, fuente: FUENTE }]);
    // Abre la versión nueva (R2) y limpia el estado de cambios.
    await esperar(() => expect(aperturas().map((a) => a.version)).toEqual(["002", "003"]));
    await esperar(() => expect(screen.getByRole("combobox", { name: "Versión" })).toHaveValue("003"));
    const region = await screen.findByRole("region", { name: "Estado del borrador" });
    await within(region).findByText(/Versión 003 · Sin cambios sin guardar/);
    expect(screen.queryByRole("button", { name: "Guardar versión…" })).toBeNull();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(screen.getByRole("tab", { name: "Parámetros" })).toHaveAttribute("aria-selected", "true");
    // El borrador guardado ya no sirve: se descarta una sola vez, y la lista de versiones se volvió a pedir.
    await esperar(() => expect(borrados()).toHaveLength(1));
    expect(fetchFalso.mock.calls.filter(([r]) => String(r).startsWith("/v1/hoja/versiones")).length).toBeGreaterThanOrEqual(2);
    // El aviso de éxito no es un `alert` que robe el foco: es un estado.
    expect(screen.getByText("Se guardó la versión 003 con 2 cambios registrados.").closest("[role='status']")).not.toBeNull();
  });

  test("3d-F2: con 1 cambio el mensaje va en singular", async () => {
    alGuardar = () => json({ codigo: "003", proyecto: "OF-001", cambios: 1, total: m("2703.86"), primera: false, mensaje: "x" });
    montar();
    const dialogo = await abrirModal();
    await escribirFuente(dialogo);
    fireEvent.click(confirmar(dialogo));
    expect(await screen.findByText("Se guardó la versión 003 con 1 cambio registrado.")).toBeInTheDocument();
  });

  test("no hay más de una petición de guardado en vuelo: el botón se deshabilita y se anuncia «Guardando la versión…»", async () => {
    let contestar: (r: Response) => void = () => undefined;
    const respuesta = new Promise<Response>((resolver) => {
      contestar = resolver;
    });
    alGuardar = () => respuesta;
    montar();
    const dialogo = await abrirModal();
    await escribirFuente(dialogo);
    const boton = confirmar(dialogo);
    fireEvent.click(boton);
    await esperar(() => expect(guardados()).toHaveLength(1));
    expect(boton).toBeDisabled();
    fireEvent.click(boton);
    fireEvent.keyDown(boton, { key: "Enter" });
    const aviso = within(dialogo).getByText("Guardando la versión…");
    expect(aviso.closest("[aria-live='polite']")).not.toBeNull();
    await act(async () => {
      await new Promise<void>((r) => setImmediate(r));
    });
    expect(guardados()).toHaveLength(1);
    versiones = VERSIONES_CON_003;
    await act(async () => contestar(json({ codigo: "003", proyecto: "OF-001", cambios: 2, total: m("2703.86"), primera: false, mensaje: "x" })));
    expect(await screen.findByText("Se guardó la versión 003 con 2 cambios registrados.")).toBeInTheDocument();
    expect(guardados()).toHaveLength(1);
  });

  test("el foco queda en el selector de versión tras guardar (el botón ya no existe)", async () => {
    montar();
    const dialogo = await abrirModal();
    await escribirFuente(dialogo);
    versiones = VERSIONES_CON_003;
    fireEvent.click(confirmar(dialogo));
    await screen.findByText("Se guardó la versión 003 con 2 cambios registrados.");
    await esperar(() => expect(screen.getByRole("combobox", { name: "Versión" })).toHaveFocus());
  });

  // --- 3d-F3: primera versión --------------------------------------------------------------------------------------------

  describe("3d-F3: proyecto sin versiones", () => {
    beforeEach(() => {
      proyectoActual = "NU-001";
      versiones = SIN_VERSIONES;
      alAbrir = (c) => (c.version === null ? borrador(null, { cambios: 4, rev: 2 }, "NU-001") : borrador(c.version, { cambios: 0, rev: 0 }, "NU-001"));
      alGuardar = () => json({ codigo: "001", proyecto: "NU-001", cambios: 1, total: m("2703.86", "2703.8602"), primera: true, mensaje: "x" });
    });

    test("ofrece «Guardar primera versión…» y su diálogo pide la fuente de la medida", async () => {
      montar();
      const dialogo = await abrirModal("Guardar primera versión…");
      expect(within(dialogo).getByRole("heading", { name: "Guardar primera versión" })).toBeInTheDocument();
      expect(within(dialogo).getByRole("textbox", { name: "Fuente de la medida (de dónde salen los datos)" })).toBeInTheDocument();
      expect(within(dialogo).getByText(/Es la primera versión del proyecto NU-001/)).toBeInTheDocument();
      expect(confirmar(dialogo, "Guardar primera versión")).toBeDisabled();
      expect(
        within(dialogo).getByText("Escriba la fuente de la medida: de dónde salen los datos (un plano, un acta)."),
      ).toBeInTheDocument();
    });

    test("guardar crea la 001, dice el mensaje de la primera versión con el total en es-VE y la abre", async () => {
      montar();
      const dialogo = await abrirModal("Guardar primera versión…");
      await escribirFuente(dialogo, "Plano A-01 rev. B");
      versiones = { ...SIN_VERSIONES, por_omision: "001", versiones: [fila("001", true)] };
      fireEvent.click(confirmar(dialogo, "Guardar primera versión"));
      expect(
        await screen.findByText(
          "Se guardó la primera versión 001 del proyecto NU-001 (total 2.703,86). Quedó registrada su creación, con su fuente y su responsable.",
        ),
      ).toBeInTheDocument();
      expect(guardados()).toEqual([{ rev: 2, fuente: "Plano A-01 rev. B" }]);
      await esperar(() => expect(aperturas().map((a) => a.version)).toEqual([null, "001"]));
      await esperar(() => expect(screen.getByRole("combobox", { name: "Versión" })).toHaveValue("001"));
    });

    test("con la hoja vacía el servidor dice por qué (422) y el diálogo sigue abierto con la fuente", async () => {
      const vacia = "La hoja esta vacia: describa o importe el espacio antes de guardar la primera version.";
      alGuardar = () => json({ detalle: vacia }, 422);
      montar();
      const dialogo = await abrirModal("Guardar primera versión…");
      await escribirFuente(dialogo, "Plano A-01");
      fireEvent.click(confirmar(dialogo, "Guardar primera versión"));
      expect(await within(dialogo).findByText(vacia)).toBeInTheDocument();
      expect(campoFuente(dialogo)).toHaveValue("Plano A-01");
    });
  });

  // --- 3d-F4: 409 de versión más nueva -----------------------------------------------------------------------------------

  describe("3d-F4: otra persona guardó una versión más nueva", () => {
    beforeEach(() => {
      alGuardar = (c) =>
        c["confirmar_version_mas_nueva"] === true
          ? json({ codigo: "005", proyecto: "OF-001", cambios: 2, total: m("2703.86"), primera: false, mensaje: "x" })
          : json({ detalle: MAS_NUEVA, version_mas_nueva: "004" }, 409);
    });

    test("avisa con el texto del servidor, no guarda nada solo y ofrece «Guardar de todos modos» y abrir la 004", async () => {
      montar();
      const dialogo = await abrirModal();
      await escribirFuente(dialogo);
      fireEvent.click(confirmar(dialogo));
      expect(await within(dialogo).findByText(MAS_NUEVA)).toBeInTheDocument();
      expect(within(dialogo).getByRole("button", { name: "Guardar de todos modos" })).toBeEnabled();
      expect(within(dialogo).getByRole("button", { name: "Abrir la versión 004" })).toBeEnabled();
      expect(within(dialogo).getByRole("alert")).toBeInTheDocument();
      await act(async () => {
        await new Promise<void>((r) => setImmediate(r));
      });
      expect(guardados()).toEqual([{ rev: 3, fuente: FUENTE }]); // una sola petición, sin confirmar
      expect(aperturas()).toHaveLength(1);
    });

    test("«Guardar de todos modos» reenvía con la confirmación y guarda", async () => {
      montar();
      const dialogo = await abrirModal();
      await escribirFuente(dialogo);
      fireEvent.click(confirmar(dialogo));
      fireEvent.click(await within(dialogo).findByRole("button", { name: "Guardar de todos modos" }));
      expect(await screen.findByText("Se guardó la versión 005 con 2 cambios registrados.")).toBeInTheDocument();
      expect(guardados()).toEqual([
        { rev: 3, fuente: FUENTE },
        { rev: 3, fuente: FUENTE, confirmar_version_mas_nueva: true },
      ]);
    });

    test("«Abrir la versión 004» cierra el diálogo y pasa por la confirmación de descartar: nada se pierde en silencio", async () => {
      versiones = { ...VERSIONES, versiones: [fila("004", true, "002"), ...VERSIONES.versiones] };
      montar();
      const dialogo = await abrirModal();
      await escribirFuente(dialogo);
      fireEvent.click(confirmar(dialogo));
      fireEvent.click(await within(dialogo).findByRole("button", { name: "Abrir la versión 004" }));
      const aviso = await screen.findByRole("alertdialog");
      expect(within(aviso).getByText(/Tiene 2 cambios sin guardar/)).toBeInTheDocument();
      expect(borrados()).toHaveLength(0);
      expect(aperturas()).toHaveLength(1);
      fireEvent.click(within(aviso).getByRole("button", { name: "Descartar y abrir" }));
      await esperar(() => expect(aperturas().map((a) => a.version)).toEqual(["002", "004"]));
      expect(borrados()).toHaveLength(1);
    });
  });

  // --- Otros resultados --------------------------------------------------------------------------------------------------

  test("409 de rev viejo: lo dice y «Recargar el borrador» vuelve a leerlo; el siguiente guardado usa el rev nuevo", async () => {
    const d = "El borrador cambió en otra ventana: vuelva a cargarlo.";
    let n = 0;
    alGuardar = () => (n++ === 0 ? json({ detalle: d }, 409) : json({ codigo: "003", proyecto: "OF-001", cambios: 2, total: m("2703.86"), primera: false, mensaje: "x" }));
    alVivo = () => {
      const b = borrador("002", { rev: 7 });
      return json({ id: ID, base: b.base, resumen: b.resumen });
    };
    montar();
    const dialogo = await abrirModal();
    await escribirFuente(dialogo);
    fireEvent.click(confirmar(dialogo));
    expect(await within(dialogo).findByText(d)).toBeInTheDocument();
    fireEvent.click(within(dialogo).getByRole("button", { name: "Recargar el borrador" }));
    await esperar(() => expect(within(dialogo).queryByText(d)).toBeNull());
    expect(campoFuente(dialogo)).toHaveValue(FUENTE);
    fireEvent.click(confirmar(dialogo));
    await screen.findByText("Se guardó la versión 003 con 2 cambios registrados.");
    expect(guardados().map((g) => g["rev"])).toEqual([3, 7]);
  });

  test("409 «ya se guardó como la versión 004»: ofrece abrirla (sin pedir descartar, ya está guardado)", async () => {
    alGuardar = () => json({ detalle: "Este borrador ya se guardó como la versión 004; abra esa versión para seguir." }, 409);
    versiones = { ...VERSIONES, versiones: [fila("004", true, "002"), ...VERSIONES.versiones] };
    montar();
    const dialogo = await abrirModal();
    await escribirFuente(dialogo);
    fireEvent.click(confirmar(dialogo));
    expect(await within(dialogo).findByText(/Este borrador ya se guardó como la versión 004/)).toBeInTheDocument();
    fireEvent.click(within(dialogo).getByRole("button", { name: "Abrir la versión 004" }));
    await esperar(() => expect(aperturas().map((a) => a.version)).toEqual(["002", "004"]));
    expect(screen.queryByRole("alertdialog")).toBeNull();
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  test.each([
    [403, "La hoja del proyecto se edita y se guarda con una cuenta; la clave de API no sirve."],
    [422, "El guardado no tiene la forma esperada: envíe rev (entero) y la fuente como texto de hasta 300 caracteres."],
    [422, "Escriba la fuente del cambio: por que se cambia y con que respaldo."],
    [409, "Esta version esta en solo lectura: alguna de sus partidas ya no tiene composicion vigente en el catalogo, asi que recalcularla cambiaria sus precios."],
    [409, "No se guardó nada: la lista de precios no tiene el insumo X."],
    [503, "No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro programa."],
  ])("un %s se muestra con el texto de la API y el diálogo sigue abierto con lo escrito", async (estado, detalle) => {
    alGuardar = () => json({ detalle }, estado);
    montar();
    const dialogo = await abrirModal();
    await escribirFuente(dialogo);
    fireEvent.click(confirmar(dialogo));
    expect(await within(dialogo).findByText(detalle)).toBeInTheDocument();
    expect(campoFuente(dialogo)).toHaveValue(FUENTE);
    expect(confirmar(dialogo)).toBeEnabled(); // se puede volver a intentar
    expect(screen.getByRole("combobox", { name: "Versión", hidden: true })).toHaveValue("002");
    expect(aperturas()).toHaveLength(1);
  });

  test("un 401 al guardar avisa al marco para que pida la sesión de nuevo", async () => {
    alGuardar = () => json({ detalle: "Inicie sesión." }, 401);
    montar();
    const dialogo = await abrirModal();
    await escribirFuente(dialogo);
    fireEvent.click(confirmar(dialogo));
    await esperar(() => expect(alExpirar).toHaveBeenCalled());
  });

  // --- 3d-F8: el borrador ya no está ------------------------------------------------------------------------------------

  test("3d-F8: un 404 de borrador al guardar muestra el mensaje del servidor, no pierde la fuente y ofrece abrir de nuevo", async () => {
    alGuardar = () => json({ detalle: FALTA }, 404);
    montar();
    const dialogo = await abrirModal();
    await escribirFuente(dialogo);
    fireEvent.click(confirmar(dialogo));
    expect(await within(dialogo).findByText(FALTA)).toBeInTheDocument();
    expect(campoFuente(dialogo)).toHaveValue(FUENTE); // el formulario no se pierde
    fireEvent.click(within(dialogo).getByRole("button", { name: "Abrir de nuevo" }));
    await esperar(() => expect(aperturas().map((a) => a.version)).toEqual(["002", "002"]));
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  test("retomar un borrador y guardarlo no vuelve a ofrecer el borrador viejo", async () => {
    fetchFalso.mockImplementation(
      ((impl) =>
        async (...args: Parameters<typeof fetch>) => {
          const url = new URL(String(args[0]), "http://silice.local");
          if (url.pathname === "/v1/hoja/borradores" && (args[1]?.method ?? "GET") === "GET") {
            return json({ borradores: [{ id: ID, proyecto: "OF-001", version: "002", cambios: 2, rev: 3, tocado: "2026-10-20T10:00:00" }] });
          }
          return impl(...args);
        })(fetchFalso.getMockImplementation()!),
    );
    montar();
    fireEvent.click(await screen.findByRole("button", { name: "Retomar borrador de OF-001 (2 cambios)" }));
    const dialogo = await abrirModal();
    await escribirFuente(dialogo);
    versiones = VERSIONES_CON_003;
    fireEvent.click(confirmar(dialogo));
    await screen.findByText("Se guardó la versión 003 con 2 cambios registrados.");
    await esperar(() => expect(screen.getByRole("combobox", { name: "Versión" })).toHaveValue("003"));
    expect(screen.queryByRole("button", { name: /Retomar borrador/ })).toBeNull();
  });

  // --- Estática ----------------------------------------------------------------------------------------------------------

  test("3d-F13: los archivos de guardar están bajo la prueba estática (sin Number, parseFloat, toFixed ni + unario)", () => {
    const fuentes = import.meta.glob("./*.{ts,tsx}", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
    for (const ruta of ["./index.tsx", "./logicaGuardar.ts", "./DialogoDeGuardar.tsx", "./useGuardado.ts", "./useDialogo.ts"]) {
      expect(Object.keys(fuentes), ruta).toContain(ruta);
      expect(fuentes[ruta], ruta).not.toMatch(
        /\bNumber\s*\(|\bparseFloat\s*\(|\bparseInt\s*\(|\.toFixed\s*\(|(?:[=(,:?]|\breturn)\s*\+\s*[A-Za-z_$(]/,
      );
    }
  });
});
