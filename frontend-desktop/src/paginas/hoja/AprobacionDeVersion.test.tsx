import { act, configure, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { cuerpoDeVista } from "./datosDePrueba";
import PaginaHoja from "./index";
import type { BorradorAbierto, Resumen, VersionesRespuesta } from "./logica";

// Tarea 19 del plan de montar un presupuesto (con los cambios por el diseño de módulos): en la Hoja, junto a la versión, la
// etiqueta de su aprobación, «Enviar a aprobación…» y, si la devolvieron, sus notas y «Hacer una versión nueva a partir de
// esta» (diseño §5.4). La API es de mentira y responde con la forma de `api/rutas/aprobaciones.py` (Tarea 18). Las etiquetas
// y los avisos están escritos a mano desde el plan. Obra ficticia OF-001 con las versiones VIV-001 y VIV-002.
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
  acciones: ["editar_hoja", "aprobar_version"],
  modo_entrega: false,
};

const ID = "id-borrador-aaaaaaaaaaaa";
const RUTA_ESTADOS = "/v1/aprobaciones?proyecto=OF-001";
const m = (texto: string, exacto = texto) => ({ texto, exacto });
const fila = (codigo: string, vigente: boolean, origen = "") => ({
  codigo,
  fecha: "2026-10-20",
  motivo: "",
  origen,
  vigente,
  descartada: false,
  cambios: 0,
});
const SOLO_001: VersionesRespuesta = { proyecto: "OF-001", moneda: "Bs", por_omision: "VIV-001", versiones: [fila("VIV-001", true)] };
const CON_002: VersionesRespuesta = {
  proyecto: "OF-001",
  moneda: "Bs",
  por_omision: "VIV-002",
  versiones: [fila("VIV-002", true, "VIV-001"), fila("VIV-001", false)],
};

function resumen(extra: Partial<Resumen> = {}): Resumen {
  return {
    rev: 3,
    moneda: "Bs",
    total: m("4876.56"),
    cambios: 0,
    pendientes_catalogo: 0,
    hallazgos: [],
    hay_plan: true,
    version_mas_nueva: null,
    guardado_como: null,
    ...extra,
  };
}

function borrador(version: string | null, extra: Partial<Resumen> = {}): BorradorAbierto {
  return {
    id: ID,
    base: { proyecto: "OF-001", version, vigente: version, lista: "Lista", espacio_de: version, solo_lectura: false, moneda: "Bs" },
    resumen: resumen(extra),
    instantanea: { creadas: 0, mensaje: null },
  };
}

interface EstadoVersion {
  estado: string;
  por: string | null;
  el: string | null;
  notas: string;
  armo: boolean;
}

const GUARDADA: EstadoVersion = { estado: "guardada", por: null, el: null, notas: "", armo: false };
const EN_APROBACION: EstadoVersion = { estado: "en_aprobacion", por: "Ana Pérez <ana>", el: "2026-10-24T09:15:00", notas: "", armo: true };
const APROBADA: EstadoVersion = { estado: "aprobada", por: "Rita <rita>", el: "2026-10-25T10:30:00", notas: "", armo: false };
const CON_OBSERVACIONES: EstadoVersion = {
  estado: "aprobada_con_observaciones",
  por: "Rita <rita>",
  el: "2026-10-25T10:30:00",
  notas: "Revise el precio del acero antes de entregar.",
  armo: false,
};
const DEVUELTA: EstadoVersion = {
  estado: "devuelta",
  por: "Rita <rita>",
  el: "2026-10-25T10:30:00",
  notas: "Falta el acero de la losa.",
  armo: false,
};
const RETIRADA: EstadoVersion = { estado: "retirada", por: "Ana Pérez <ana>", el: "2026-10-24T11:00:00", notas: "", armo: true };

function estados(versiones: Record<string, EstadoVersion>) {
  return { rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." }, fases: "", versiones, eventos: [] };
}

const CADENA_ROTA =
  "No se puede enviar VIV-001: la cadena de versiones de esta obra está rota en la versión VIV-001 (el sello no coincide). Revíselo con el administrador.";

describe("Tarea 19: la aprobación de la versión en la Hoja", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  const alExpirar = vi.fn();
  let versiones: VersionesRespuesta;
  let aprobaciones: Record<string, EstadoVersion>;
  let alLeerEstados: () => Response;
  let alAbrir: (cuerpo: { proyecto: string; version: string | null }) => BorradorAbierto;
  let alEnviar: (cuerpo: Record<string, unknown>) => Response;
  let alGuardar: () => Response;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    versiones = SOLO_001;
    aprobaciones = { "VIV-001": GUARDADA };
    alLeerEstados = () => json(estados(aprobaciones));
    alAbrir = (c) => borrador(c.version);
    alEnviar = (c) => {
      // La versión pasa a «en aprobación» en el servidor; la que estaba pendiente queda retirada.
      aprobaciones = { ...aprobaciones, [String(c["version"])]: { ...EN_APROBACION, el: "2026-10-26T08:00:00" } };
      return json({ id: 7, estado: "en_aprobacion", retirada: null }, 201);
    };
    alGuardar = () => json({ codigo: "VIV-002", proyecto: "OF-001", cambios: 1, total: m("5000.00"), primera: false, mensaje: "x" });
    fetchFalso.mockImplementation(async (ruta, init) => {
      const texto = String(ruta);
      const url = new URL(texto, "http://silice.local");
      const metodo = init?.method ?? "GET";
      const camino = url.pathname;
      if (camino === "/v1/aprobaciones" && metodo === "GET") return alLeerEstados();
      if (camino === "/v1/aprobaciones" && metodo === "POST") return alEnviar(JSON.parse(String(init?.body)) as Record<string, unknown>);
      if (camino === "/v1/hoja/versiones") return json(versiones);
      if (camino === "/v1/hoja/borradores" && metodo === "GET") return json({ borradores: [] });
      if (camino === "/v1/hoja/borradores" && metodo === "POST") {
        return json(alAbrir(JSON.parse(String(init?.body)) as { proyecto: string; version: string | null }), 201);
      }
      if (camino.endsWith("/cambios")) return json({ rev: 3, cambios: [] });
      if (camino.endsWith("/guardar") && metodo === "POST") return alGuardar();
      const vista = cuerpoDeVista(texto);
      if (vista !== null) return json(vista);
      const propio = /^\/v1\/hoja\/borradores\/([^/]+)$/.exec(camino);
      if (propio && metodo === "DELETE") return new Response(null, { status: 204 });
      return json({ detalle: "No encontrado." }, 404);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  const llamadas = (metodo: string, ruta: string) =>
    fetchFalso.mock.calls.filter(([r, init]) => String(r) === ruta && (init?.method ?? "GET") === metodo);
  const envios = () => llamadas("POST", "/v1/aprobaciones").map(([, i]) => JSON.parse(String(i?.body)) as Record<string, unknown>);

  function valor(): Aplicacion {
    return {
      sesion: SESION,
      proyecto: "OF-001",
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

  const region = () => screen.findByRole("region", { name: "Aprobación de la versión" });
  const etiqueta = async () => (await region()).querySelector(".silice-hoja__aprobacion-etiqueta");
  async function textoDeEtiqueta(): Promise<string | null> {
    return esperar(() => {
      const e = document.querySelector(".silice-hoja__aprobacion-etiqueta");
      if (e === null) throw new Error("sin etiqueta");
      return e.textContent;
    });
  }

  describe("la etiqueta, exacta", () => {
    test.each([
      ["guardada", GUARDADA, "Guardada"],
      ["en aprobación (sin «quien la armó»: el envío siempre es de quien la armó)", EN_APROBACION, "En aprobación"],
      ["aprobada", APROBADA, "Aprobada · Rita · 25/10/2026"],
      ["aprobada con observaciones", CON_OBSERVACIONES, "Aprobada con observaciones · Rita · 25/10/2026"],
      ["devuelta", DEVUELTA, "Devuelta · Rita · 25/10/2026"],
    ])("%s", async (_n, estado, esperado) => {
      aprobaciones = { "VIV-001": estado };
      montar();
      expect(await textoDeEtiqueta()).toBe(esperado);
      expect(await etiqueta()).not.toBeNull();
    });

    test("aprobada por quien la armó: lo dice", async () => {
      aprobaciones = { "VIV-001": { ...APROBADA, por: "Ana Pérez <ana>", armo: true } };
      montar();
      expect(await textoDeEtiqueta()).toBe("Aprobada · Ana Pérez · 25/10/2026 · aprobada por quien la armó");
    });

    // Menor del arbitro de T19.
    test("devuelta por quien la armó: lo dice", async () => {
      aprobaciones = { "VIV-001": { ...DEVUELTA, por: "Ana Pérez <ana>", armo: true } };
      montar();
      expect(await textoDeEtiqueta()).toBe("Devuelta · Ana Pérez · 25/10/2026 · devuelta por quien la armó");
    });

    test("se pide el estado de la obra abierta (GET /v1/aprobaciones?proyecto=)", async () => {
      montar();
      await textoDeEtiqueta();
      expect(llamadas("GET", RUTA_ESTADOS)).toHaveLength(1);
    });

    test("con aprobada con observaciones se leen las notas", async () => {
      aprobaciones = { "VIV-001": CON_OBSERVACIONES };
      montar();
      expect(await region()).toHaveTextContent("Notas de Rita: Revise el precio del acero antes de entregar.");
    });

    test("un borrador en blanco (sin versión guardada) no tiene aprobación ni la pide", async () => {
      versiones = { proyecto: "OF-001", moneda: "Bs", por_omision: null, versiones: [] };
      alAbrir = () => borrador(null, { cambios: 1 });
      montar();
      await screen.findByRole("region", { name: "Estado del borrador" });
      await new Promise((r) => setTimeout(r, 30));
      expect(screen.queryByRole("region", { name: "Aprobación de la versión" })).toBeNull();
      expect(llamadas("GET", RUTA_ESTADOS)).toEqual([]);
    });

    test("si el servidor no puede leer el estado, lo dice sin tumbar la Hoja", async () => {
      alLeerEstados = () => json({ detalle: "No se pudo leer o guardar la aprobación en la carpeta de trabajo." }, 503);
      montar();
      expect(await region()).toHaveTextContent("No se pudo leer el estado de aprobación de esta versión.");
      expect(screen.queryByRole("button", { name: "Enviar a aprobación…" })).toBeNull();
      expect(screen.getByRole("region", { name: "Estado del borrador" })).toBeInTheDocument();
    });
  });

  describe("«Enviar a aprobación…»", () => {
    test.each([
      ["guardada", GUARDADA, true],
      ["retirada", RETIRADA, true],
      ["en aprobación", EN_APROBACION, false],
      ["aprobada", APROBADA, false],
      ["aprobada con observaciones", CON_OBSERVACIONES, false],
      ["devuelta", DEVUELTA, false],
    ])("%s → ¿se ofrece? %s", async (_n, estado, ofrece) => {
      aprobaciones = { "VIV-001": estado };
      montar();
      await textoDeEtiqueta();
      expect(screen.queryByRole("button", { name: "Enviar a aprobación…" }) !== null).toBe(ofrece);
    });

    test("es un diálogo: foco en la nota, el resto inerte; enviar manda POST /v1/aprobaciones y la etiqueta pasa a «En aprobación»", async () => {
      const u = userEvent.setup();
      montar();
      await u.click(await screen.findByRole("button", { name: "Enviar a aprobación…" }));
      const dialogo = await screen.findByRole("dialog", { name: "Enviar a aprobación" });
      expect(dialogo).toHaveAttribute("aria-modal", "true");
      const nota = within(dialogo).getByRole("textbox", { name: "Nota para quien revisa (opcional)" });
      expect(nota).toHaveFocus();
      expect(nota).toHaveAttribute("maxlength", "2000");
      expect(screen.getByRole("combobox", { name: "Versión", hidden: true }).closest("[inert]")).not.toBeNull();
      expect(dialogo).toHaveTextContent("Quien revisa verá la versión VIV-001 tal como se guardó y dará su dictamen.");
      await u.type(nota, "Lista para revisar.");
      await u.click(within(dialogo).getByRole("button", { name: "Enviar a aprobación" }));
      await esperar(() => expect(screen.queryByRole("dialog")).toBeNull());
      expect(envios()).toEqual([{ proyecto: "OF-001", version: "VIV-001", nota: "Lista para revisar." }]);
      await esperar(() => expect(document.querySelector(".silice-hoja__aprobacion-etiqueta")).toHaveTextContent("En aprobación"));
      const estado = within(await region()).getByRole("status");
      expect(estado).toHaveTextContent("Se envió VIV-001 a aprobación.");
      // Ya no se ofrece enviar la misma versión otra vez.
      expect(screen.queryByRole("button", { name: "Enviar a aprobación…" })).toBeNull();
      // El aviso no es una notificación verde: texto neutro.
      expect(document.querySelector(".cds--inline-notification--success")).toBeNull();
    });

    test("sin nota se manda la nota vacía", async () => {
      const u = userEvent.setup();
      montar();
      await u.click(await screen.findByRole("button", { name: "Enviar a aprobación…" }));
      const dialogo = await screen.findByRole("dialog", { name: "Enviar a aprobación" });
      await u.click(within(dialogo).getByRole("button", { name: "Enviar a aprobación" }));
      await esperar(() => expect(envios()).toEqual([{ proyecto: "OF-001", version: "VIV-001", nota: "" }]));
    });

    // F4, Tarea 3, ronda 2 (mayor del árbitro): la obra ya no se vuelve a montar al cambiar de sección, así que tras
    // enviar se pide otra vez su ficha (la cabecera dice la etapa nueva). Montada sola, sin obra, no pide nada.
    test("dentro de una obra, enviar vuelve a leer la ficha de la obra", async () => {
      const u = userEvent.setup();
      const recargarFicha = vi.fn();
      render(
        <ContextoAplicacion.Provider value={valor()}>
          <ContextoDeLaObra.Provider value={{ carpeta: null, obraId: 1, ficha: { estado: "cargando" }, recargarFicha }}>
            <PaginaHoja />
          </ContextoDeLaObra.Provider>
        </ContextoAplicacion.Provider>,
      );
      await u.click(await screen.findByRole("button", { name: "Enviar a aprobación…" }));
      const dialogo = await screen.findByRole("dialog", { name: "Enviar a aprobación" });
      expect(recargarFicha).not.toHaveBeenCalled();
      await u.click(within(dialogo).getByRole("button", { name: "Enviar a aprobación" }));
      await esperar(() => expect(envios()).toHaveLength(1));
      await esperar(() => expect(recargarFicha).toHaveBeenCalledTimes(1));
    });

    test("con `retirada` avisa «Se retiró VIV-001 de la aprobación.»", async () => {
      const u = userEvent.setup();
      versiones = CON_002;
      aprobaciones = { "VIV-001": EN_APROBACION, "VIV-002": GUARDADA };
      alEnviar = () => {
        aprobaciones = { "VIV-001": RETIRADA, "VIV-002": { ...EN_APROBACION, el: "2026-10-26T08:00:00" } };
        return json({ id: 8, estado: "en_aprobacion", retirada: "VIV-001" }, 201);
      };
      montar();
      await u.click(await screen.findByRole("button", { name: "Enviar a aprobación…" }));
      const dialogo = await screen.findByRole("dialog", { name: "Enviar a aprobación" });
      await u.click(within(dialogo).getByRole("button", { name: "Enviar a aprobación" }));
      const estado = await within(await region()).findByRole("status");
      await esperar(() => expect(estado).toHaveTextContent("Se envió VIV-002 a aprobación. Se retiró VIV-001 de la aprobación."));
      expect(envios()).toEqual([{ proyecto: "OF-001", version: "VIV-002", nota: "" }]);
    });

    test("Esc cierra sin enviar y el foco vuelve a «Enviar a aprobación…»; Tab no sale del diálogo", async () => {
      const u = userEvent.setup();
      montar();
      const boton = await screen.findByRole("button", { name: "Enviar a aprobación…" });
      await u.click(boton);
      const dialogo = await screen.findByRole("dialog", { name: "Enviar a aprobación" });
      const enviar = within(dialogo).getByRole("button", { name: "Enviar a aprobación" });
      enviar.focus();
      await u.tab();
      expect(within(dialogo).getByRole("textbox", { name: "Nota para quien revisa (opcional)" })).toHaveFocus();
      await u.tab({ shift: true });
      expect(enviar).toHaveFocus();
      await u.keyboard("{Escape}");
      await esperar(() => expect(screen.queryByRole("dialog")).toBeNull());
      await esperar(() => expect(screen.getByRole("button", { name: "Enviar a aprobación…" })).toHaveFocus());
      expect(envios()).toEqual([]);
    });

    test("«Cancelar» cierra sin enviar", async () => {
      const u = userEvent.setup();
      montar();
      await u.click(await screen.findByRole("button", { name: "Enviar a aprobación…" }));
      await u.click(within(await screen.findByRole("dialog", { name: "Enviar a aprobación" })).getByRole("button", { name: "Cancelar" }));
      await esperar(() => expect(screen.queryByRole("dialog")).toBeNull());
      expect(envios()).toEqual([]);
    });

    test("un 409 (cadena rota) se dice en el diálogo con el texto del servidor y la versión sigue «Guardada»", async () => {
      const u = userEvent.setup();
      alEnviar = () => json({ detalle: CADENA_ROTA }, 409);
      montar();
      await u.click(await screen.findByRole("button", { name: "Enviar a aprobación…" }));
      const dialogo = await screen.findByRole("dialog", { name: "Enviar a aprobación" });
      await u.click(within(dialogo).getByRole("button", { name: "Enviar a aprobación" }));
      expect(await within(dialogo).findByRole("alert")).toHaveTextContent(CADENA_ROTA);
      expect(screen.getByRole("dialog", { name: "Enviar a aprobación" })).toBeInTheDocument();
      expect(await textoDeEtiqueta()).toBe("Guardada");
    });

    test("un 401 al enviar avisa al marco", async () => {
      const u = userEvent.setup();
      alEnviar = () => json({ detalle: "Su sesión venció." }, 401);
      montar();
      await u.click(await screen.findByRole("button", { name: "Enviar a aprobación…" }));
      const dialogo = await screen.findByRole("dialog", { name: "Enviar a aprobación" });
      await u.click(within(dialogo).getByRole("button", { name: "Enviar a aprobación" }));
      await esperar(() => expect(alExpirar).toHaveBeenCalled());
    });

    // Tarea 5 del plan F4 (regla 2 de la franja): con cambios sin guardar el paso es guardarlos; enviar no se ofrece hasta
    // entonces. Antes se ofrecía y el diálogo avisaba que los cambios no viajaban.
    test("con cambios sin guardar no se ofrece enviar: la franja pide guardar antes", async () => {
      alAbrir = (c) => borrador(c.version, { cambios: 2 });
      montar();
      const franja = await screen.findByRole("region", { name: "Siguiente paso" });
      expect(franja).toHaveTextContent("Siguiente paso: Hay 2 cambios sin guardar");
      expect(within(franja).getByRole("button", { name: "Guardar versión…" })).toBeInTheDocument();
      await textoDeEtiqueta();
      expect(screen.queryByRole("button", { name: "Enviar a aprobación…" })).toBeNull();
    });
  });

  describe("devuelta: las notas y una versión nueva", () => {
    // Tarea 5 del plan F4: el botón está en la franja del paso y se llama «Hacer una versión nueva».
    test("se leen las notas y «Hacer una versión nueva» (de la franja) lleva a «Partidas» con el aviso", async () => {
      const u = userEvent.setup();
      aprobaciones = { "VIV-001": DEVUELTA };
      montar();
      const zona = await region();
      expect(zona).toHaveTextContent("Notas de Rita: Falta el acero de la losa.");
      expect(screen.getByRole("tab", { name: "Partidas" })).toHaveAttribute("aria-selected", "false");
      const franja = screen.getByRole("region", { name: "Siguiente paso" });
      await u.click(within(franja).getByRole("button", { name: "Hacer una versión nueva" }));
      await esperar(() => expect(screen.getByRole("tab", { name: "Partidas" })).toHaveAttribute("aria-selected", "true"));
      expect(within(zona).getByRole("status")).toHaveTextContent("Corrija y guarde: será una versión nueva.");
      // No reabre ni envía nada: el borrador de esa versión ya está abierto.
      expect(envios()).toEqual([]);
      expect(llamadas("POST", "/v1/hoja/borradores")).toHaveLength(1);
    });

    test("foco 3: la devuelta y sus notas siguen ahí al salir y volver a entrar (se vuelven a leer de la API)", async () => {
      aprobaciones = { "VIV-001": DEVUELTA };
      const vista = montar();
      expect(await textoDeEtiqueta()).toBe("Devuelta · Rita · 25/10/2026");
      vista.unmount();
      montar();
      expect(await textoDeEtiqueta()).toBe("Devuelta · Rita · 25/10/2026");
      expect(await region()).toHaveTextContent("Notas de Rita: Falta el acero de la losa.");
      expect(llamadas("GET", RUTA_ESTADOS)).toHaveLength(2);
    });
  });

  test("la versión enviada no se edita: con VIV-001 «En aprobación», guardar un cambio crea VIV-002 y VIV-001 sigue «En aprobación»", async () => {
    aprobaciones = { "VIV-001": EN_APROBACION };
    alAbrir = (c) => borrador(c.version, { cambios: 1 });
    montar();
    expect(await textoDeEtiqueta()).toBe("En aprobación");
    expect(await region()).toHaveTextContent("La versión enviada no se edita: si guarda cambios, será una versión nueva.");
    // Se guarda el cambio (una cantidad) con su fuente.
    fireEvent.click(await screen.findByRole("button", { name: "Guardar versión…" }));
    const dialogo = await screen.findByRole("dialog");
    fireEvent.change(within(dialogo).getByRole("textbox", { name: /^Fuente/ }), { target: { value: "Medición en obra del 25/10/2026" } });
    versiones = CON_002;
    aprobaciones = { "VIV-001": EN_APROBACION, "VIV-002": GUARDADA };
    alAbrir = (c) => borrador(c.version, { cambios: 0, rev: 0 });
    fireEvent.click(within(dialogo).getByRole("button", { name: "Guardar versión" }));
    await esperar(() => expect(screen.getByRole("combobox", { name: "Versión" })).toHaveValue("VIV-002"));
    await esperar(() => expect(document.querySelector(".silice-hoja__aprobacion-etiqueta")).toHaveTextContent("Guardada"));
    expect(screen.getByRole("button", { name: "Enviar a aprobación…" })).toBeInTheDocument();
    // Guardar no toca la aprobación.
    expect(envios()).toEqual([]);
    // VIV-001 sigue «En aprobación».
    fireEvent.change(screen.getByRole("combobox", { name: "Versión" }), { target: { value: "VIV-001" } });
    await esperar(() => expect(document.querySelector(".silice-hoja__aprobacion-etiqueta")).toHaveTextContent("En aprobación"));
  });

  test("ningún archivo de la aprobación convierte un texto en número", () => {
    const fuentes = import.meta.glob("./AprobacionDeVersion*.tsx", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
    expect(Object.keys(fuentes)).toContain("./AprobacionDeVersion.tsx");
    for (const [ruta, codigo] of Object.entries(fuentes)) {
      if (ruta.endsWith(".test.tsx")) continue;
      expect(codigo, ruta).not.toMatch(/\bNumber\s*\(|\bparseFloat\s*\(|\bparseInt\s*\(|\.toFixed\s*\(/);
    }
  });
});
