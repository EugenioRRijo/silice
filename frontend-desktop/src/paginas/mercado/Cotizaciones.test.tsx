import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import type { ObraAbierta } from "../../marco/obraAbierta";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { preciosRespuesta } from "../hoja/datosDePrueba";
import type { PreciosRespuesta, VersionesRespuesta } from "../hoja/logica";
import PaginaMercado from "./index";

// Tarea 13 del plan F4 (preguntas 4 y 8 del inventario): las cotizaciones de la obra viven en Mercado, sobre la versión
// VIGENTE. El servidor se simula con respuestas ficticias (obra OF-001). La conversión de moneda no cambia: el precio
// original, la tasa del día exacto del precio, su fecha y su fuente se ven como en Presupuesto › Precios.

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const sesion = (acciones: string[]): SesionRespuesta => ({
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones,
  modo_entrega: false,
});
const EDITA = sesion(["editar_hoja", "leer_proyecto"]);
const REVISA = sesion(["leer_proyecto"]);

const fila = (codigo: string, vigente: boolean) => ({ codigo, fecha: "2026-10-06", motivo: "", origen: "", vigente, descartada: false, cambios: 0 });
const VERSIONES: VersionesRespuesta = { proyecto: "OF-001", moneda: "USD", por_omision: "002", versiones: [fila("002", true), fila("001", false)] };
const SIN_VERSIONES: VersionesRespuesta = { ...VERSIONES, por_omision: null, versiones: [] };

// MAT-002 tiene una cotización propia en bolívares convertida con la tasa del día del precio; MAT-001 no.
function precios(): PreciosRespuesta {
  const base = preciosRespuesta();
  return {
    ...base,
    filas: base.filas.map((f) =>
      f["codigo"] === "MAT-002"
        ? {
            ...f,
            cotizacion: "COT-17 · Ferretería Demo",
            moneda_original: "Bs",
            precio_original: { texto: "6016.69", exacto: "6016.6918" },
            tasa: { texto: "633.36", exacto: "633.3644" },
            fecha_tasa: "2026-10-05",
            fuente_tasa: "BCV, publicación del 05/10/2026",
          }
        : f,
    ),
  };
}

const OBRA = { carpeta: null, obraId: 3, ficha: { estado: "sin_dato" }, recargarFicha: vi.fn() } as ObraAbierta;

const fetchFalso = vi.fn<typeof fetch>();
const alExpirar = vi.fn();
let versiones: VersionesRespuesta;
let alOperacion: (ruta: string) => Response | Promise<Response>;
// Los borradores que el servidor conserva de esta ficha (`GET /v1/hoja/borradores`): los cambios sin guardar del Presupuesto.
let borradores: unknown[];

const posts = (termina: string) =>
  fetchFalso.mock.calls
    .filter(([r, init]) => String(r).endsWith(termina) && init?.method === "POST")
    .map(([, i]) => JSON.parse(String(i?.body)) as Record<string, unknown>);

function montar(s: SesionRespuesta = EDITA, proyecto: string | null = "OF-001") {
  const valor: Aplicacion = { sesion: s, proyecto, caso: { nombre: "obra", ruta_relativa: "data/obra.db" }, recargarProyectos: vi.fn(), alExpirar };
  render(
    <ContextoAplicacion.Provider value={valor}>
      <ContextoDeLaObra.Provider value={OBRA}>
        <MemoryRouter>
          <PaginaMercado />
        </MemoryRouter>
      </ContextoDeLaObra.Provider>
    </ContextoAplicacion.Provider>,
  );
}

async function abrirPestana() {
  await userEvent.click(screen.getByRole("tab", { name: "Cotizaciones de la obra" }));
}
const abrirDialogo = async (nombre: string) => {
  fireEvent.click(await screen.findByRole("button", { name: nombre }));
  return screen.findByRole("dialog");
};

describe("Mercado › Cotizaciones de la obra", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    alExpirar.mockReset();
    fijarCsrf("tok");
    versiones = VERSIONES;
    borradores = [];
    alOperacion = () => json({ codigo: "003", proyecto: "OF-001", mensaje: "mensaje del servidor" });
    fetchFalso.mockImplementation(async (ruta, init) => {
      const url = new URL(String(ruta), "http://silice.local");
      if (url.pathname === "/v1/hoja/versiones" && (init?.method ?? "GET") === "GET") return json(versiones);
      if (url.pathname.startsWith("/v1/hoja/versiones/") && init?.method === "POST") return alOperacion(url.pathname);
      if (url.pathname === "/v1/hoja/precios") return json(precios());
      if (url.pathname === "/v1/hoja/borradores" && (init?.method ?? "GET") === "GET") return json({ borradores });
      return json({ detail: `Ruta no simulada: ${String(ruta)}` }, 404);
    });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("muestra las cotizaciones de la versión vigente con el rastro de la conversión, en es-VE", async () => {
    montar();
    await abrirPestana();
    const tabla = await screen.findByRole("table", { name: "Cotizaciones de la obra" });
    expect(within(tabla).getByText("COT-17 · Ferretería Demo")).toBeInTheDocument();
    expect(within(tabla).queryByText("Tubo PVC 1/2")).toBeNull(); // sin cotización propia no es una cotización
    // Original, tasa, fecha y fuente: nada se sobrescribe y se convierte al leer.
    expect(within(tabla).getByText("6.016,69")).toBeInTheDocument();
    expect(within(tabla).getByText("633,3644")).toBeInTheDocument();
    expect(within(tabla).getByText("05/10/2026")).toBeInTheDocument();
    expect(within(tabla).getByText("BCV, publicación del 05/10/2026")).toBeInTheDocument();
    const pedidos = fetchFalso.mock.calls.map(([r]) => String(r));
    expect(pedidos).toContain("/v1/hoja/precios?proyecto=OF-001&version=002");
  });

  test("una cuenta que revisa ve las cotizaciones sin «Registrar» ni «Retirar» (cotizar exige editar_hoja)", async () => {
    montar(REVISA);
    await abrirPestana();
    await screen.findByRole("table", { name: "Cotizaciones de la obra" });
    expect(screen.queryByRole("button", { name: "Registrar una cotización…" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Retirar una cotización…" })).toBeNull();
  });

  // Ronda 2 de la Tarea 13 (decisión 6): cotizar crea una versión nueva desde la vigente guardada. Si el Presupuesto de la obra
  // tiene un borrador con cambios sin guardar, se quedarían en un borrador de una versión vieja; se dice, como en la clásica.
  test("con cambios sin guardar en el Presupuesto de la obra no se ofrece cotizar y se dice por qué", async () => {
    borradores = [
      { id: "b-1", proyecto: "OF-001", version: "002", cambios: 3, tocado: "2026-11-02T09:00:00" },
      { id: "b-2", proyecto: "OF-009", version: "001", cambios: 5, tocado: "2026-11-02T09:00:00" },
    ];
    montar();
    await abrirPestana();
    await screen.findByRole("table", { name: "Cotizaciones de la obra" });
    expect(
      await screen.findByText(
        "Cotizar crea una versión nueva desde la guardada: guarde o descarte primero los 3 cambios pendientes. Están en el Presupuesto de esta obra.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Registrar una cotización…" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Retirar una cotización…" })).toBeNull();
  });

  test("los borradores sin cambios o de otra obra no impiden cotizar", async () => {
    borradores = [
      { id: "b-1", proyecto: "OF-001", version: "002", cambios: 0, tocado: "2026-11-02T09:00:00" },
      { id: "b-2", proyecto: "OF-009", version: "001", cambios: 5, tocado: "2026-11-02T09:00:00" },
    ];
    montar();
    await abrirPestana();
    expect(await screen.findByRole("button", { name: "Registrar una cotización…" })).toBeInTheDocument();
    expect(screen.queryByText(/cambios pendientes/)).toBeNull();
  });

  test("una obra sin versiones guardadas lo dice y no ofrece cotizar ni da error", async () => {
    versiones = SIN_VERSIONES;
    montar();
    await abrirPestana();
    expect(await screen.findByText("Esta obra aún no tiene versiones guardadas.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Registrar una cotización…" })).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
  });

  test("sin obra elegida pide elegir una y no lee nada del servidor", async () => {
    montar(EDITA, null);
    await abrirPestana();
    expect(await screen.findByText("Elija una obra para ver sus cotizaciones.")).toBeInTheDocument();
    expect(fetchFalso.mock.calls.filter(([r]) => String(r).startsWith("/v1/hoja"))).toHaveLength(0);
  });

  test("«Registrar una cotización…» manda la versión vigente, avisa y enlaza a la versión nueva en el Presupuesto", async () => {
    montar();
    await abrirPestana();
    const dialogo = await abrirDialogo("Registrar una cotización…");
    expect(dialogo).toHaveAccessibleName("Registrar una cotización");
    fireEvent.change(within(dialogo).getByRole("combobox", { name: "Insumo" }), { target: { value: "MAT-001" } });
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Precio cotizado" }), { target: { value: "1.003,50" } });
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Proveedor" }), { target: { value: "Ferretería Demo, C.A." } });
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Número de la cotización" }), { target: { value: "COT-18" } });
    fireEvent.change(within(dialogo).getByLabelText("Fecha de la cotización"), { target: { value: "2026-10-18" } });
    versiones = { ...VERSIONES, por_omision: "003", versiones: [fila("003", true), fila("002", false), fila("001", false)] };
    fireEvent.click(within(dialogo).getByRole("button", { name: "Cotizar" }));
    expect(await screen.findByText("Se creó la versión 003 con la cotización.")).toBeInTheDocument();
    expect(posts("/cotizar")).toEqual([
      { proyecto: "OF-001", version: "002", insumo: "MAT-001", precio: "1.003,50", proveedor: "Ferretería Demo, C.A.", numero: "COT-18", fecha: "2026-10-18", evidencia: null },
    ]);
    expect(screen.getByRole("link", { name: "Abrirla en el Presupuesto" })).toHaveAttribute("href", "/obra/empresa/3/presupuesto?version=003");
    expect(screen.queryByRole("dialog")).toBeNull();
    // La lista de versiones se volvió a leer: la vigente ya es la 003.
    await waitFor(() => expect(fetchFalso.mock.calls.map(([r]) => String(r))).toContain("/v1/hoja/precios?proyecto=OF-001&version=003"));
  });

  test("«Retirar una cotización…» ofrece los insumos cotizados, manda el motivo y avisa sin la cotización", async () => {
    montar();
    await abrirPestana();
    const dialogo = await abrirDialogo("Retirar una cotización…");
    expect(within(dialogo).getAllByRole("option").map((o) => o.textContent)).toEqual(["MAT-002 · Llave de paso (COT-17 · Ferretería Demo)"]);
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Por qué se retira" }), { target: { value: "La cotización venció" } });
    fireEvent.click(within(dialogo).getByRole("button", { name: "Retirar cotización" }));
    expect(await screen.findByText("Se creó la versión 003 sin la cotización.")).toBeInTheDocument();
    expect(posts("/retirar-cotizacion")).toEqual([{ proyecto: "OF-001", version: "002", insumo: "MAT-002", motivo: "La cotización venció" }]);
    expect(screen.getByRole("link", { name: "Abrirla en el Presupuesto" })).toHaveAttribute("href", "/obra/empresa/3/presupuesto?version=003");
  });

  test("un rechazo del servidor se muestra tal cual en el diálogo, que sigue abierto", async () => {
    alOperacion = () => json({ detalle: "precio: 'tres' no es un numero decimal valido" }, 422);
    montar();
    await abrirPestana();
    const dialogo = await abrirDialogo("Registrar una cotización…");
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Precio cotizado" }), { target: { value: "tres" } });
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Proveedor" }), { target: { value: "Ferretería Demo, C.A." } });
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Número de la cotización" }), { target: { value: "COT-18" } });
    fireEvent.click(within(dialogo).getByRole("button", { name: "Cotizar" }));
    expect(await within(dialogo).findByText("precio: 'tres' no es un numero decimal valido")).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBe(dialogo);
    expect(screen.queryByText(/Se creó la versión/)).toBeNull();
  });

  test("el diálogo deja inerte el resto de la pantalla, atrapa el foco y Esc devuelve el foco al botón", async () => {
    montar();
    await abrirPestana();
    const dialogo = await abrirDialogo("Registrar una cotización…");
    expect(dialogo).toHaveAttribute("aria-modal", "true");
    expect(dialogo.closest("[inert]")).toBeNull();
    expect(screen.getByRole("tab", { name: "Lo que compramos", hidden: true }).closest("[inert]")).not.toBeNull();
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
    await waitFor(() => expect(screen.getByRole("button", { name: "Registrar una cotización…" })).toHaveFocus());
    expect(document.querySelector("[inert]")).toBeNull();
  });

  test("falta algo: «Cotizar» queda deshabilitado y dice qué falta, en el orden del formulario", async () => {
    montar();
    await abrirPestana();
    const dialogo = await abrirDialogo("Registrar una cotización…");
    const cotizar = within(dialogo).getByRole("button", { name: "Cotizar" });
    expect(cotizar).toBeDisabled();
    expect(within(dialogo).getByText("Escriba el precio cotizado.")).toBeInTheDocument();
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Precio cotizado" }), { target: { value: "1.003,50" } });
    expect(within(dialogo).getByText("Escriba el proveedor de la cotización.")).toBeInTheDocument();
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Proveedor" }), { target: { value: "Ferretería Demo, C.A." } });
    expect(within(dialogo).getByText("Escriba el número de la cotización.")).toBeInTheDocument();
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Número de la cotización" }), { target: { value: "COT-18" } });
    expect(cotizar).toBeEnabled();
    expect(within(dialogo).getByText("Escriba los decimales con coma: 2,5; el punto separa los miles: 1.234,56.")).toBeInTheDocument();
  });

  test.each([
    [409, "No se guardó nada: la composición de la partida AF-LLAVE ya no está vigente."],
    [403, "Su cuenta no tiene permiso para esta acción."],
  ])("un %i muestra el texto del servidor tal cual y no cierra el diálogo", async (estado, detalle) => {
    alOperacion = () => json({ detalle }, estado);
    montar();
    await abrirPestana();
    const dialogo = await abrirDialogo("Registrar una cotización…");
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Precio cotizado" }), { target: { value: "10" } });
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Proveedor" }), { target: { value: "Ferretería Demo, C.A." } });
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Número de la cotización" }), { target: { value: "COT-18" } });
    fireEvent.click(within(dialogo).getByRole("button", { name: "Cotizar" }));
    expect(await within(dialogo).findByText(detalle)).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBe(dialogo);
  });

  // Ronda 3 de la Tarea 13: las pruebas de errores, sesión y petición en vuelo que tenía Precios (Hoja › Versiones) pasan aquí.
  async function llenarCotizacion(dialogo: HTMLElement, extra: Record<string, string> = {}) {
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Precio cotizado" }), { target: { value: "10" } });
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Proveedor" }), { target: { value: "Ferretería Demo, C.A." } });
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Número de la cotización" }), { target: { value: "COT-18" } });
    for (const [nombre, valor] of Object.entries(extra)) fireEvent.change(within(dialogo).getByRole("textbox", { name: new RegExp(nombre) }), { target: { value: valor } });
  }

  test.each([
    [404, "El proyecto «OF-001» no existe en este caso."],
    [503, "No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro programa."],
  ])("un %i muestra el texto del servidor tal cual y no cierra el diálogo", async (estado, detalle) => {
    alOperacion = () => json({ detalle }, estado);
    montar();
    await abrirPestana();
    const dialogo = await abrirDialogo("Registrar una cotización…");
    await llenarCotizacion(dialogo);
    fireEvent.click(within(dialogo).getByRole("button", { name: "Cotizar" }));
    expect(await within(dialogo).findByText(detalle)).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toBe(dialogo);
  });

  test("un 401 al cotizar avisa al marco para que pida la sesión de nuevo", async () => {
    alOperacion = () => json({ detalle: "Sesión vencida." }, 401);
    montar();
    await abrirPestana();
    const dialogo = await abrirDialogo("Registrar una cotización…");
    await llenarCotizacion(dialogo);
    fireEvent.click(within(dialogo).getByRole("button", { name: "Cotizar" }));
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("una sola petición en vuelo: todo queda deshabilitado, Esc no cierra y el error no se pierde", async () => {
    let contestar: (r: Response) => void = () => undefined;
    alOperacion = () =>
      new Promise<Response>((resolver) => {
        contestar = resolver;
      });
    montar();
    await abrirPestana();
    const dialogo = await abrirDialogo("Registrar una cotización…");
    await llenarCotizacion(dialogo);
    const cotizar = within(dialogo).getByRole("button", { name: "Cotizar" });
    fireEvent.click(cotizar);
    await waitFor(() => expect(posts("/cotizar")).toHaveLength(1));
    expect(cotizar).toBeDisabled();
    expect(within(dialogo).getByRole("button", { name: "Cancelar" })).toBeDisabled();
    fireEvent.click(cotizar);
    await userEvent.keyboard("{Escape}");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(within(dialogo).getByText("Guardando la versión…").closest("[aria-live='polite']")).not.toBeNull();
    await act(async () => contestar(json({ detalle: "precio: '' no es un numero decimal valido" }, 422)));
    expect(await within(screen.getByRole("dialog")).findByText("precio: '' no es un numero decimal valido")).toBeInTheDocument();
    expect(posts("/cotizar")).toHaveLength(1);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  test("con evidencia, la manda tal cual en el cuerpo", async () => {
    montar();
    await abrirPestana();
    const dialogo = await abrirDialogo("Registrar una cotización…");
    await llenarCotizacion(dialogo, { Evidencia: "correo del 18" });
    fireEvent.click(within(dialogo).getByRole("button", { name: "Cotizar" }));
    await waitFor(() => expect(posts("/cotizar")).toHaveLength(1));
    expect(posts("/cotizar")[0]!["evidencia"]).toBe("correo del 18");
  });

  test("Tab no sale del diálogo y Mayús+Tab hace lo inverso", async () => {
    montar();
    await abrirPestana();
    const dialogo = await abrirDialogo("Registrar una cotización…");
    await llenarCotizacion(dialogo);
    const u = userEvent.setup({ delay: null });
    const cotizar = within(dialogo).getByRole("button", { name: "Cotizar" });
    cotizar.focus();
    await u.tab();
    expect(within(dialogo).getByRole("combobox", { name: "Insumo" })).toHaveFocus();
    await u.tab({ shift: true });
    expect(cotizar).toHaveFocus();
  });

  test("los archivos de la tarea no calculan (sin Number, parseFloat, toFixed ni + unario)", () => {
    const fuentes = import.meta.glob("./*.tsx", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
    for (const ruta of ["./CotizacionesDeLaObra.tsx", "./OperacionesDePrecios.tsx", "./HistoricoDePrecios.tsx"]) {
      const texto = fuentes[ruta];
      expect(texto, ruta).toBeDefined();
      expect(texto, ruta).not.toMatch(/\bNumber\(|parseFloat|toFixed|\(\+\w/);
    }
  });
});
