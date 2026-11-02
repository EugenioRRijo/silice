import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { formulariosSucios, olvidarFormularios } from "../../shell/sucio";
import PaginaAprobar from "./index";

// Tarea 20: la pantalla «Aprobar una versión» (`/aprobar?envio=`). Lee el envío en solo lectura (`GET
// /v1/aprobaciones/{id}`, api/rutas/aprobaciones.py) y registra el dictamen (`POST /v1/aprobaciones/{id}/dictamen`).
// Datos ficticios.

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const SESION: SesionRespuesta = {
  login: "rita",
  nombre: "Rita Gómez",
  roles: ["revisa"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["leer_proyecto", "revisar_paquete", "aprobar_version"],
  modo_entrega: false,
};

const SIN_NOTAS = "Escriba las notas: son obligatorias para devolver o aprobar con observaciones.";

function detalle(parcial: Record<string, unknown> = {}) {
  return {
    envio_id: 12,
    proyecto: "3",
    obra: "Galpón Sur",
    version: "GS-001",
    estado: "en_aprobacion",
    moneda: "Bs",
    total: "4876.56257",
    partidas: [
      {
        codigo: "E.411.000.111",
        descripcion: "Concreto de f'c 250 kgf/cm2 para losas",
        unidad: "m3",
        cantidad: "12.5",
        precio_unitario: "1234.5678",
        total: "15432.0975",
        pendiente: false,
      },
      {
        codigo: "PEND-1",
        descripcion: "Bote de escombros",
        unidad: "m3",
        cantidad: "3",
        precio_unitario: null,
        total: null,
        pendiente: true,
      },
    ],
    hallazgos: {
      error: 1,
      advertencia: 1,
      info: 0,
      lista: [
        { regla: "R3", severidad: "error", descripcion: "El precio unitario no cuadra con su análisis." },
        { regla: "R7", severidad: "advertencia", descripcion: "Rendimiento fuera del rango típico." },
      ],
    },
    rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." },
    cadena: { integra: true, mensaje: "Cadena íntegra: 1 versión verificada." },
    envio: { por: "Ana Pérez <ana>", el: "2026-10-20T09:15:00", nota: "Revise el acero, por favor." },
    armo: false,
    ...parcial,
  };
}

const fetchFalso = vi.fn<typeof fetch>();
let detalleDe: (id: string) => Response;
let alDictaminar: (cuerpo: unknown) => Response;
let pendientes: () => Response;
const alExpirar = vi.fn();

beforeEach(() => {
  fijarCsrf("tok");
  vi.stubGlobal("fetch", fetchFalso);
  fetchFalso.mockReset();
  alExpirar.mockReset();
  detalleDe = () => json(detalle());
  alDictaminar = (cuerpo) => json({ id: 30, estado: (cuerpo as { resultado: string }).resultado }, 201);
  pendientes = () => json([]);
  fetchFalso.mockImplementation(async (entrada, init) => {
    const url = new URL(String(entrada), "http://x");
    const metodo = init?.method ?? "GET";
    if (metodo === "GET" && url.pathname === "/v1/aprobaciones/pendientes") return pendientes();
    const dictamen = /^\/v1\/aprobaciones\/(\d+)\/dictamen$/.exec(url.pathname);
    if (metodo === "POST" && dictamen) {
      const cuerpo = JSON.parse(String(init?.body)) as unknown;
      const r = alDictaminar(cuerpo);
      if (r.status === 201) {
        const resultado = (cuerpo as { resultado: string }).resultado;
        detalleDe = () => json(detalle({ estado: resultado }));
      }
      return r;
    }
    const uno = /^\/v1\/aprobaciones\/(\d+)$/.exec(url.pathname);
    if (metodo === "GET" && uno) return detalleDe(uno[1]);
    return json({ detalle: "No encontrado." }, 404);
  });
});

afterEach(() => {
  olvidarFormularios();
  vi.unstubAllGlobals();
  fijarCsrf(null);
});

function Ubicacion() {
  const { pathname, search } = useLocation();
  return <p data-testid="ubicacion">{`${pathname}${search}`}</p>;
}

function montar(ruta = "/aprobar?envio=12", parcial: Partial<Aplicacion> = {}, recargarFicha?: () => void) {
  const aplicacion: Aplicacion = {
    sesion: SESION,
    proyecto: null,
    caso: { nombre: "s2.db", ruta_relativa: "casos/s2.db" },
    recargarProyectos: vi.fn(),
    alExpirar,
    ...parcial,
  };
  const pagina = (
    <MemoryRouter initialEntries={[ruta]}>
      <Routes>
        <Route
          path="/aprobar"
          element={
            <>
              <PaginaAprobar />
              <Ubicacion />
            </>
          }
        />
      </Routes>
    </MemoryRouter>
  );
  return render(
    <ContextoAplicacion.Provider value={aplicacion}>
      {recargarFicha ? (
        <ContextoDeLaObra.Provider value={{ carpeta: null, obraId: 3, ficha: { estado: "cargando" }, recargarFicha }}>
          {pagina}
        </ContextoDeLaObra.Provider>
      ) : (
        pagina
      )}
    </ContextoAplicacion.Provider>,
  );
}

const dictamenes = () =>
  fetchFalso.mock.calls.filter(([, init]) => init?.method === "POST").map(([e, init]) => [String(e), JSON.parse(String(init?.body))]);

async function panel() {
  return screen.findByRole("region", { name: "Dictamen" });
}

describe("lo que se aprueba, en solo lectura", () => {
  test("la cabecera del envío dice la obra, la versión, la carpeta, el total, quién la envió y su nota", async () => {
    montar();
    expect(screen.getByRole("heading", { level: 1, name: "Aprobar una versión" })).toBeInTheDocument();
    const envio = await screen.findByRole("region", { name: "Galpón Sur · GS-001" });
    expect(within(envio).getByText("s2")).toBeInTheDocument(); // T19, punto 4: de qué carpeta es
    expect(within(envio).getByText("Carpeta")).toBeInTheDocument();
    expect(within(envio).getByText("4.876,56 Bs")).toBeInTheDocument();
    expect(within(envio).getByText("Ana Pérez, el 20/10/2026 09:15")).toBeInTheDocument();
    expect(within(envio).getByText("En aprobación")).toBeInTheDocument();
    expect(within(envio).getByText("«Revise el acero, por favor.»")).toBeInTheDocument();
    expect(within(envio).getByText("Rastro de aprobaciones íntegro.")).toBeInTheDocument();
    expect(fetchFalso.mock.calls.map(([e]) => String(e))).toContain("/v1/aprobaciones/12");
  });

  test("las partidas con coma decimal y punto de miles, sin `title` con punto; el ítem pendiente dice que no tiene precio", async () => {
    montar();
    const tabla = await screen.findByRole("table", { name: "Partidas de GS-001" });
    const filas = within(tabla).getAllByRole("row");
    const concreto = filas.find((f) => f.textContent?.includes("E.411.000.111"))!;
    expect(within(concreto).getByText("12,5")).toBeInTheDocument();
    expect(within(concreto).getByText("1.234,57")).toBeInTheDocument();
    expect(within(concreto).getByText("15.432,10")).toBeInTheDocument();
    const pendiente = filas.find((f) => f.textContent?.includes("PEND-1"))!;
    expect(within(pendiente).getByText("Sin precio")).toBeInTheDocument();
    for (const conTitulo of document.querySelectorAll("[title]")) {
      expect(conTitulo.getAttribute("title"), "un title con punto decimal").not.toMatch(/\d\.\d/);
    }
  });

  test("los hallazgos con el informe de auditoría", async () => {
    montar();
    const informe = await screen.findByRole("region", { name: "Informe de auditoría" });
    expect(informe).toHaveTextContent("Presupuesto GS-001 · Hallazgos: 2 · Resultado: NO CUMPLE");
    expect(within(informe).getByText("El precio unitario no cuadra con su análisis.")).toBeInTheDocument();
  });

  test("no hay campos para editar la versión: el único campo de la pantalla son las notas del dictamen", async () => {
    montar();
    await panel();
    expect(screen.getAllByRole("textbox").map((c) => c.id)).toEqual(["aprobar-notas"]);
    expect(screen.queryByRole("spinbutton")).toBeNull();
    expect(screen.queryByRole("button", { name: /guardar/i })).toBeNull();
  });

  test("si quien mira armó la versión, el panel lo dice", async () => {
    detalleDe = () => json(detalle({ armo: true }));
    montar();
    expect(await within(await panel()).findByText("Usted armó esta versión: el dictamen quedará rotulado así.")).toBeInTheDocument();
  });

  test("sin `armo` no lo dice", async () => {
    montar();
    expect(within(await panel()).queryByText(/Usted armó esta versión/)).toBeNull();
  });
});

describe("el dictamen", () => {
  test.each([["Devuelta"], ["Aprobada con observaciones"]])("«%s» sin notas no se envía: el campo lo dice y recibe el foco", async (opcion) => {
    const u = userEvent.setup();
    montar();
    const caja = await panel();
    await u.click(within(caja).getByRole("radio", { name: opcion }));
    await u.click(within(caja).getByRole("button", { name: "Registrar el dictamen…" }));
    const notas = within(caja).getByRole("textbox", { name: /Notas/ });
    expect(await within(caja).findByText(SIN_NOTAS)).toBeInTheDocument();
    expect(notas).toHaveAttribute("aria-invalid", "true");
    expect(notas).toHaveFocus();
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(dictamenes()).toEqual([]);
  });

  test("sin elegir el dictamen no se envía y lo pide", async () => {
    const u = userEvent.setup();
    montar();
    const caja = await panel();
    await u.click(within(caja).getByRole("button", { name: "Registrar el dictamen…" }));
    expect(await within(caja).findByText("Elija el dictamen: aprobada, aprobada con observaciones o devuelta.")).toBeInTheDocument();
    expect(within(caja).getByRole("radio", { name: "Aprobada" })).toHaveFocus();
    expect(dictamenes()).toEqual([]);
  });

  test("devolver con notas pide confirmación, envía el dictamen y lo dice en texto neutro (sin aviso verde)", async () => {
    const u = userEvent.setup();
    montar();
    const caja = await panel();
    await u.click(within(caja).getByRole("radio", { name: "Devuelta" }));
    await u.type(within(caja).getByRole("textbox", { name: /Notas/ }), "Falta el acero de la losa.");
    const boton = within(caja).getByRole("button", { name: "Registrar el dictamen…" });
    await u.click(boton);
    const dialogo = await screen.findByRole("dialog", { name: "Registrar el dictamen" });
    expect(dialogo).toHaveTextContent("GS-001 de Galpón Sur quedará devuelta. El dictamen no se cambia después.");
    expect(within(dialogo).getByRole("button", { name: "Volver" })).toHaveFocus();
    expect(dictamenes()).toEqual([]);
    await u.click(within(dialogo).getByRole("button", { name: "Registrar el dictamen" }));
    await waitFor(() =>
      expect(dictamenes()).toEqual([["/v1/aprobaciones/12/dictamen", { resultado: "devuelta", notas: "Falta el acero de la losa." }]]),
    );
    expect(await screen.findByText("Dictamen registrado: GS-001 devuelta.")).toBeInTheDocument();
    expect(document.querySelector(".cds--inline-notification--success")).toBeNull();
    // Se vuelve a leer el envío: ya tiene dictamen y no se ofrece otro.
    const despues = await panel();
    expect(await within(despues).findByText("Este envío ya tiene dictamen: Devuelta.")).toBeInTheDocument();
    expect(within(despues).queryByRole("button", { name: "Registrar el dictamen…" })).toBeNull();
  });

  // F4, Tarea 3 (menor 1 del árbitro): la obra ya no se vuelve a montar al cambiar de sección; tras un dictamen, la línea
  // «Estado:» de la cabecera se actualiza si se vuelve a leer la ficha. Sin obra abierta (la pantalla sola) no hay ficha.
  test("dentro de una obra, registrar el dictamen vuelve a leer la ficha de la obra", async () => {
    const u = userEvent.setup();
    const recargarFicha = vi.fn();
    montar("/aprobar?envio=12", {}, recargarFicha);
    const caja = await panel();
    await u.click(within(caja).getByRole("radio", { name: "Aprobada" }));
    await u.click(within(caja).getByRole("button", { name: "Registrar el dictamen…" }));
    const dialogo = await screen.findByRole("dialog", { name: "Registrar el dictamen" });
    expect(recargarFicha).not.toHaveBeenCalled();
    await u.click(within(dialogo).getByRole("button", { name: "Registrar el dictamen" }));
    await waitFor(() => expect(recargarFicha).toHaveBeenCalledTimes(1));
  });

  test("un dictamen que el servidor rechaza no vuelve a leer la ficha", async () => {
    const u = userEvent.setup();
    const recargarFicha = vi.fn();
    alDictaminar = () => json({ detalle: "Ya tiene dictamen." }, 409);
    montar("/aprobar?envio=12", {}, recargarFicha);
    const caja = await panel();
    await u.click(within(caja).getByRole("radio", { name: "Aprobada" }));
    await u.click(within(caja).getByRole("button", { name: "Registrar el dictamen…" }));
    const dialogo = await screen.findByRole("dialog", { name: "Registrar el dictamen" });
    await u.click(within(dialogo).getByRole("button", { name: "Registrar el dictamen" }));
    await waitFor(() => expect(dictamenes()).toHaveLength(1));
    await screen.findByText("Ya tiene dictamen.");
    expect(recargarFicha).not.toHaveBeenCalled();
  });

  test("aprobar sin notas se permite", async () => {
    const u = userEvent.setup();
    montar();
    const caja = await panel();
    await u.click(within(caja).getByRole("radio", { name: "Aprobada" }));
    await u.click(within(caja).getByRole("button", { name: "Registrar el dictamen…" }));
    const dialogo = await screen.findByRole("dialog", { name: "Registrar el dictamen" });
    expect(dialogo).toHaveTextContent("GS-001 de Galpón Sur quedará aprobada.");
    await u.click(within(dialogo).getByRole("button", { name: "Registrar el dictamen" }));
    await waitFor(() => expect(dictamenes()).toEqual([["/v1/aprobaciones/12/dictamen", { resultado: "aprobada", notas: "" }]]));
  });

  test("«Volver» y Esc cierran la confirmación sin enviar y el foco vuelve al botón", async () => {
    const u = userEvent.setup();
    montar();
    const caja = await panel();
    await u.click(within(caja).getByRole("radio", { name: "Aprobada" }));
    const boton = within(caja).getByRole("button", { name: "Registrar el dictamen…" });
    await u.click(boton);
    await u.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Volver" }));
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(boton).toHaveFocus();
    await u.click(boton);
    await screen.findByRole("dialog");
    await u.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(dictamenes()).toEqual([]);
  });

  test("un rechazo del servidor (409) se dice con su texto y el dictamen escrito se conserva", async () => {
    const u = userEvent.setup();
    alDictaminar = () => json({ detalle: "Este envío ya tiene dictamen o fue retirado." }, 409);
    montar();
    const caja = await panel();
    await u.click(within(caja).getByRole("radio", { name: "Devuelta" }));
    await u.type(within(caja).getByRole("textbox", { name: /Notas/ }), "Corregir.");
    await u.click(within(caja).getByRole("button", { name: "Registrar el dictamen…" }));
    await u.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Registrar el dictamen" }));
    expect(await within(caja).findByText("Este envío ya tiene dictamen o fue retirado.")).toBeInTheDocument();
    expect(within(caja).getByRole("textbox", { name: /Notas/ })).toHaveValue("Corregir.");
  });

  test("las notas escritas cuentan como cambios sin guardar de esta pantalla", async () => {
    const u = userEvent.setup();
    montar();
    const caja = await panel();
    expect(formulariosSucios()).toEqual([]);
    await u.type(within(caja).getByRole("textbox", { name: /Notas/ }), "Algo");
    expect(formulariosSucios()).toEqual(["aprobar"]);
  });

  test("un envío ya cerrado no ofrece dictamen", async () => {
    detalleDe = () => json(detalle({ estado: "aprobada_con_observaciones" }));
    montar();
    const caja = await panel();
    expect(await within(caja).findByText("Este envío ya tiene dictamen: Aprobada con observaciones.")).toBeInTheDocument();
    expect(within(caja).queryByRole("radio")).toBeNull();
  });

  test("un envío retirado lo dice", async () => {
    detalleDe = () => json(detalle({ estado: "retirada" }));
    montar();
    expect(await within(await panel()).findByText("Este envío fue retirado: se envió otra versión de la obra.")).toBeInTheDocument();
  });

  test("con la cadena de versiones rota solo se ofrece devolver y se dice por qué", async () => {
    detalleDe = () => json(detalle({ cadena: { integra: false, mensaje: "Cadena rota en la versión GS-001: no tiene eslabón." } }));
    montar();
    const caja = await panel();
    expect(await within(caja).findByText(/Cadena rota en la versión GS-001: no tiene eslabón\./)).toBeInTheDocument();
    expect(within(caja).getByText(/Aprobar queda bloqueado hasta reparar la cadena; devolver no certifica nada\./)).toBeInTheDocument();
    expect(within(caja).queryByRole("radio", { name: "Aprobada" })).toBeNull();
    expect(within(caja).queryByRole("radio", { name: "Aprobada con observaciones" })).toBeNull();
    expect(within(caja).getAllByRole("radio")).toHaveLength(1);
    expect(within(caja).getByRole("radio", { name: "Devuelta" })).toBeChecked();
  });

  test("con la cadena rota devolver pide notas y envía solo la devolución", async () => {
    const u = userEvent.setup();
    detalleDe = () => json(detalle({ cadena: { integra: false, mensaje: "Cadena rota en la versión GS-001: no tiene eslabón." } }));
    montar();
    const caja = await panel();
    await u.click(await within(caja).findByRole("button", { name: "Registrar el dictamen…" }));
    expect(within(caja).getByText(SIN_NOTAS)).toBeInTheDocument();
    expect(dictamenes()).toEqual([]);
    await u.type(within(caja).getByRole("textbox", { name: /Notas/ }), "La cadena está rota.");
    await u.click(within(caja).getByRole("button", { name: "Registrar el dictamen…" }));
    await u.click(within(await screen.findByRole("dialog")).getByRole("button", { name: "Registrar el dictamen" }));
    await waitFor(() =>
      expect(dictamenes()).toEqual([["/v1/aprobaciones/12/dictamen", { resultado: "devuelta", notas: "La cadena está rota." }]]),
    );
  });
});

describe("cómo se llega", () => {
  test("un envío que no está en esta carpeta (404) lo dice", async () => {
    detalleDe = () => json({ detalle: "No se encontró ese envío." }, 404);
    montar();
    expect(await screen.findByText("No se encontró ese envío.")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Dictamen" })).toBeNull();
  });

  const fila = (caso: string, envio_id: number, proyecto: string, obra: string, version: string) => ({
    caso,
    envio_id,
    proyecto,
    obra,
    version,
    total: "100",
    moneda: "Bs",
    estado: "en_aprobacion",
    enviado_por: "Ana Pérez <ana>",
    enviado_el: "2026-10-20T09:15:00",
    dictamen_por: null,
    dictamen_el: null,
    nota: "",
    notas: "",
    armo: false,
  });

  test("T19, punto 5: sin `?envio=`, toma el envío en aprobación de la obra elegida en esta carpeta", async () => {
    pendientes = () => json([fila("silice.db", 4, "3", "Otra de la empresa", "X-001"), fila("s2.db", 12, "3", "Galpón Sur", "GS-001")]);
    montar("/aprobar", { proyecto: "3" });
    expect(await screen.findByRole("region", { name: "Galpón Sur · GS-001" })).toBeInTheDocument();
    expect(screen.getByTestId("ubicacion")).toHaveTextContent("/aprobar?envio=12");
  });

  test("sin `?envio=` ni envío de la obra elegida, lista los de esta carpeta y abre el que se elija", async () => {
    const u = userEvent.setup();
    pendientes = () => json([fila("s2.db", 12, "3", "Galpón Sur", "GS-001"), fila("s1.db", 2, "1", "Torre", "T-001")]);
    montar("/aprobar", { proyecto: "9" });
    const lista = await screen.findByRole("list", { name: "Versiones que esperan dictamen en esta carpeta" });
    expect(within(lista).getAllByRole("listitem")).toHaveLength(1);
    expect(screen.getByText("Hay 1 envío en otras carpetas: ábralo desde Pendientes.")).toBeInTheDocument();
    await u.click(within(lista).getByRole("button", { name: "Abrir el envío" }));
    expect(await screen.findByRole("region", { name: "Galpón Sur · GS-001" })).toBeInTheDocument();
    expect(screen.getByTestId("ubicacion")).toHaveTextContent("/aprobar?envio=12");
  });

  test("T19, punto 5: sin `?envio=` y sin el índice (403), quien arma lo halla en el rastro de la obra elegida", async () => {
    pendientes = () => json({ detalle: "Su cuenta no puede hacer esto." }, 403);
    const rastro = {
      rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." },
      fases: "GS-001 en aprobación",
      versiones: {},
      eventos: [{ id: 12, tipo: "envio", version: "GS-001", resultado: null, notas: "", por: "Ana Pérez <ana>", el: "2026-10-20T09:15:00", armo: false, cierre_de: null }],
    };
    const anterior = fetchFalso.getMockImplementation()!;
    fetchFalso.mockImplementation(async (entrada, init) =>
      String(entrada) === "/v1/aprobaciones?proyecto=3" ? json(rastro) : anterior(entrada, init),
    );
    montar("/aprobar", { proyecto: "3", sesion: { ...SESION, acciones: [...SESION.acciones, "editar_hoja"] } });
    expect(await screen.findByRole("region", { name: "Galpón Sur · GS-001" })).toBeInTheDocument();
    expect(screen.getByTestId("ubicacion")).toHaveTextContent("/aprobar?envio=12");
  });

  test("sin `?envio=`, sin índice y sin `editar_hoja`, no pide el rastro y lo dice", async () => {
    pendientes = () => json({ detalle: "Falla." }, 503);
    montar("/aprobar", { proyecto: "3" });
    expect(await screen.findByText("No se pudieron leer los envíos por aprobar")).toBeInTheDocument();
    expect(fetchFalso.mock.calls.map(([e]) => String(e)).some((u) => u.startsWith("/v1/aprobaciones?"))).toBe(false);
  });

  test("sin envíos en ninguna carpeta lo dice", async () => {
    montar("/aprobar");
    expect(await screen.findByText("No hay versiones esperando dictamen.")).toBeInTheDocument();
  });
});

// Tarea 6 del plan F4: el rastro de aprobaciones de la obra se muda de la pestaña «Trazabilidad» de la Hoja a esta
// sección. Lo ve toda cuenta con `leer_proyecto` (desde la Tarea 2b `GET /v1/aprobaciones?proyecto=` lo exige), dentro
// de la obra abierta. Datos ficticios.
describe("Rastro de la obra (Tarea 6 del plan F4)", () => {
  const RASTRO = {
    rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." },
    fases: "GS-001 en aprobación",
    versiones: { "GS-001": { estado: "en_aprobacion", por: null, el: null, notas: "", armo: false } },
    eventos: [{ id: 12, tipo: "envio", version: "GS-001", resultado: null, notas: "", por: "Ana Pérez <ana>", el: "2026-10-20T09:15:00", armo: false, cierre_de: null }],
    ultima_aprobada: null,
  };
  const conRastro = () => {
    const anterior = fetchFalso.getMockImplementation()!;
    fetchFalso.mockImplementation(async (entrada, init) =>
      String(entrada) === "/v1/aprobaciones?proyecto=3" ? json(RASTRO) : anterior(entrada, init),
    );
  };

  test("con la sesión de «revisa», dentro de la obra, se ve el h2 «Rastro de la obra» con las fases y los movimientos", async () => {
    conRastro();
    montar("/aprobar?envio=12", { proyecto: "3" }, vi.fn());
    const titulo = await screen.findByRole("heading", { level: 2, name: "Rastro de la obra" });
    expect(titulo).toHaveClass("cds--type-heading-compact-02");
    const region = screen.getByRole("region", { name: "Rastro de la obra" });
    expect(await within(region).findByText("GS-001 en aprobación")).toBeInTheDocument();
    expect(within(region).getByText("Rastro de aprobaciones íntegro.")).toBeInTheDocument();
    expect(within(region).getByRole("table", { name: "Movimientos de aprobación" })).toBeInTheDocument();
    expect(region.querySelector("svg")).not.toBeNull(); // el color nunca va solo
  });

  test("sin `leer_proyecto` no se ve ni se pide", async () => {
    conRastro();
    montar("/aprobar?envio=12", { proyecto: "3", sesion: { ...SESION, acciones: ["aprobar_version"] } }, vi.fn());
    await screen.findByRole("region", { name: "Galpón Sur · GS-001" });
    await new Promise((r) => setTimeout(r, 20));
    expect(screen.queryByRole("heading", { name: "Rastro de la obra" })).toBeNull();
    expect(fetchFalso.mock.calls.map(([e]) => String(e))).not.toContain("/v1/aprobaciones?proyecto=3");
  });
});
