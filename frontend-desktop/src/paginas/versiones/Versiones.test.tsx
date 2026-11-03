import { act, configure, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../../api/cliente";
import type { SesionRespuesta } from "../../api/tipos";
import { ContextoDeLaObra } from "../../marco/obraAbierta";
import { ofertaDe, seccionesDeLaObra } from "../../marco/oferta";
import { ContextoAplicacion } from "../../shell/contexto";
import type { Aplicacion } from "../../shell/contexto";
import { ACCIONES } from "../../shell/obras/datosDePrueba";
import { olvidarFormularios } from "../../shell/sucio";
import { trazabilidadRespuesta } from "../hoja/datosDePrueba";
import type { BorradorAbierto, VersionFila, VersionesRespuesta } from "../hoja/logica";
import { ProveedorDeLaHoja } from "../hoja/ProveedorDeLaHoja";
import PaginaVersiones from "./index";

// Tarea 6 del plan F4: la sección Versiones de la obra. Lee el borrador y las versiones del proveedor de la obra
// (`ProveedorDeLaHoja`), el estado de aprobación de cada versión (`GET /v1/aprobaciones?proyecto=`), la cadena de sellos
// (`GET /v1/hoja/cadena`) y, en el panel, el registro de cambios de una versión (`GET /v1/hoja/trazabilidad`). Obra
// ficticia 3 de la carpeta de la empresa, versiones VIV-001 y VIV-002 (la vigente). Los oráculos están escritos a mano
// desde el plan; los del registro de cambios y de restaurar vienen de las pruebas de la pestaña «Trazabilidad» de la Hoja,
// que esta sección absorbe (bajas 9 y 24).
configure({ asyncUtilTimeout: 5000 });

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const ARMA: SesionRespuesta = {
  login: "ana",
  nombre: "Ana Pérez",
  roles: ["arma"],
  csrf: "tok",
  debe_cambiar_clave: false,
  acciones: ["editar_hoja", "leer_proyecto"],
  modo_entrega: false,
};
const REVISA: SesionRespuesta = { ...ARMA, login: "rita", nombre: "Rita Gómez", roles: ["revisa"], acciones: ["leer_proyecto"] };

const fila = (codigo: string, fecha: string, motivo: string, origen: string, vigente: boolean, cambios: number): VersionFila => ({
  codigo,
  fecha,
  motivo,
  origen,
  vigente,
  descartada: false,
  cambios,
});

const VIV_002 = fila("VIV-002", "2026-10-21", "edicion", "VIV-001", true, 4);
const VIV_001 = fila("VIV-001", "2026-10-20", "", "", false, 0);

const estado = (e: string) => ({ estado: e, por: null, el: null, notas: "", armo: false });

const CADENA_INTEGRA = { integra: true, mensaje: "Cadena íntegra: 2 versiones", declaracion: null, rota_en: null };
const CADENA_ROTA = {
  integra: false,
  mensaje:
    "Cadena rota en la versión VIV-002: su registro de cambios no coincide con su huella; alguien cambió la base fuera del sistema. Revíselo con el administrador antes de entregar un paquete.",
  declaracion: null,
  rota_en: "VIV-002",
};

let versiones: VersionesRespuesta;
let aprobaciones: () => Response;
let cadena: () => Response;
let trazabilidad: (version: string) => Response;
let cambiosAlAbrir: number;
let soloLectura: boolean;
let alRestaurar: (cuerpo: Record<string, unknown>) => Response;
const fetchFalso = vi.fn<typeof fetch>();

function borrador(version: string | null): BorradorAbierto {
  return {
    id: `b-${version ?? "blanco"}`,
    base: { proyecto: "3", version, vigente: "VIV-002", lista: "Lista", espacio_de: version, solo_lectura: soloLectura, moneda: "Bs" },
    resumen: {
      rev: 1,
      moneda: "Bs",
      total: { texto: "1234.50", exacto: "1234.5" },
      cambios: cambiosAlAbrir,
      pendientes_catalogo: 0,
      hallazgos: [],
      hay_plan: true,
      version_mas_nueva: null,
      guardado_como: null,
      espacio_vacio: true,
    },
    instantanea: { creadas: 0, mensaje: null },
  };
}

beforeEach(() => {
  fijarCsrf("tok");
  vi.stubGlobal("fetch", fetchFalso);
  fetchFalso.mockReset();
  versiones = { proyecto: "3", moneda: "Bs", por_omision: "VIV-002", versiones: [VIV_002, VIV_001] };
  aprobaciones = () =>
    json({
      rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." },
      fases: "VIV-001 devuelta",
      versiones: { "VIV-001": estado("devuelta"), "VIV-002": estado("guardada") },
      eventos: [],
      ultima_aprobada: null,
    });
  cadena = () => json(CADENA_INTEGRA);
  trazabilidad = () => json(trazabilidadRespuesta());
  cambiosAlAbrir = 0;
  soloLectura = false;
  alRestaurar = () => json({ codigo: "VIV-003", proyecto: "3", mensaje: "La versión VIV-001 se restauró como la versión VIV-003 (la vigente)." });
  fetchFalso.mockImplementation(async (entrada, init) => {
    const url = new URL(String(entrada), "http://silice.local");
    const metodo = init?.method ?? "GET";
    const camino = url.pathname;
    if (camino === "/v1/hoja/versiones" && metodo === "GET") return json(versiones);
    if (camino === "/v1/hoja/versiones/restaurar" && metodo === "POST") {
      return alRestaurar(JSON.parse(String(init?.body)) as Record<string, unknown>);
    }
    if (camino === "/v1/hoja/borradores" && metodo === "GET") return json({ borradores: [] });
    if (camino === "/v1/hoja/borradores" && metodo === "POST") {
      const pedido = JSON.parse(String(init?.body)) as { version: string | null };
      return json(borrador(pedido.version), 201);
    }
    if (camino.endsWith("/cambios")) return json({ cambios: [] });
    if (/^\/v1\/hoja\/borradores\/[^/]+$/.test(camino) && metodo === "DELETE") return new Response(null, { status: 204 });
    if (camino === "/v1/aprobaciones") return aprobaciones();
    if (camino === "/v1/hoja/cadena") return cadena();
    if (camino === "/v1/hoja/trazabilidad") return trazabilidad(url.searchParams.get("version") ?? "");
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
  return <output data-testid="ruta">{`${pathname}${search}`}</output>;
}

// La sección como la monta EspacioDeObra: dentro de la obra 3 de la empresa y del proveedor de la Hoja. Las demás rutas no
// pintan nada: así «Abrir» deja ver adónde fue sin que otra pantalla consuma el `?version=`.
function montar(sesion: SesionRespuesta = ARMA) {
  const aplicacion: Aplicacion = { sesion, proyecto: "3", caso: null, recargarProyectos: vi.fn(), alExpirar: vi.fn() };
  render(
    <ContextoAplicacion.Provider value={aplicacion}>
      <ContextoDeLaObra.Provider value={{ carpeta: null, obraId: 3, ficha: { estado: "cargando" }, recargarFicha: vi.fn() }}>
        <MemoryRouter initialEntries={["/obra/empresa/3/versiones"]}>
          <Routes>
            <Route
              path="/obra/:carpeta/:obraId/versiones"
              element={
                <ProveedorDeLaHoja>
                  <PaginaVersiones />
                </ProveedorDeLaHoja>
              }
            />
            <Route path="*" element={null} />
          </Routes>
          <Ubicacion />
        </MemoryRouter>
      </ContextoDeLaObra.Provider>
    </ContextoAplicacion.Provider>,
  );
  return userEvent.setup();
}

const ruta = () => screen.getByTestId("ruta").textContent;
const tabla = () => screen.findByRole("table", { name: "Versiones de la obra" });
// Las celdas de datos de cada renglón (sin la de las acciones), en el orden de la tabla.
async function celdas() {
  const t = await tabla();
  return within(t)
    .getAllByRole("row")
    .slice(1)
    .map((r) => Array.from(r.querySelectorAll("td")).slice(0, 7).map((c) => c.textContent));
}
const renglon = async (codigo: string) =>
  within(await tabla())
    .getAllByRole("row")
    .find((r) => r.querySelector("td")?.textContent?.startsWith(codigo))!;
const pausa = () =>
  act(async () => {
    await new Promise((r) => setTimeout(r, 30));
  });
// El borrador ya está abierto (su lectura llegó) y la tabla tiene los estados.
const listo = () => waitFor(() => expect(fetchFalso.mock.calls.some(([e]) => String(e).startsWith("/v1/aprobaciones"))).toBe(true));

describe("Versiones: la tabla de las versiones de la obra", () => {
  test("un h1 «Versiones» y una tabla con las siete columnas (y la de las acciones)", async () => {
    montar();
    expect(screen.getAllByRole("heading", { level: 1 }).map((h) => h.textContent)).toEqual(["Versiones"]);
    const t = await tabla();
    expect(within(t).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
      "Versión",
      "Fecha",
      "Motivo",
      "Sale de",
      "Cambios",
      "Estado de aprobación",
      "Vigente",
      "Acciones",
    ]);
    await waitFor(async () =>
      expect(await celdas()).toEqual([
        ["VIV-002 (abierta)", "21/10/2026", "edicion", "VIV-001", "4", "Guardada", "Sí"],
        ["VIV-001", "20/10/2026", "elaborada", "", "0", "Devuelta", ""],
      ]),
    );
  });

  test("«Abrir» en VIV-001 lleva al Presupuesto de la obra con esa versión", async () => {
    const u = montar();
    await listo();
    await u.click(within(await renglon("VIV-001")).getByRole("button", { name: "Abrir VIV-001" }));
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/3/presupuesto?version=VIV-001"));
  });

  test("con VIV-001 abierta y VIV-002 vigente, la fila de VIV-001 dice «abierta» (Foco 5)", async () => {
    versiones = { ...versiones, por_omision: "VIV-001" };
    montar();
    await waitFor(async () => expect((await celdas()).map((c) => c[0])).toEqual(["VIV-002", "VIV-001 (abierta)"]));
    expect((await celdas())[0]![6]).toBe("Sí");
  });

  test("si las aprobaciones no se pueden leer, la columna de estado queda vacía y el resto se pinta, sin un aviso que la tape", async () => {
    aprobaciones = () => json({ detalle: "Falla." }, 503);
    montar();
    await listo();
    await pausa();
    expect((await celdas()).map((c) => c[5])).toEqual(["", ""]);
    expect((await celdas()).map((c) => c[0])).toEqual(["VIV-002 (abierta)", "VIV-001"]);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  test("una obra sin versiones muestra su estado vacío y ningún error (Foco 2)", async () => {
    versiones = { proyecto: "3", moneda: "Bs", por_omision: null, versiones: [] };
    montar();
    expect(await screen.findByText("Esta obra aún no tiene versiones guardadas.")).toBeInTheDocument();
    await pausa();
    expect(screen.queryByRole("table", { name: "Versiones de la obra" })).toBeNull();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});

describe("Versiones: el registro de cambios en el panel", () => {
  test("«Ver cambios» abre el panel «Registro de cambios de la versión VIV-002» con las filas de la trazabilidad", async () => {
    const u = montar();
    await listo();
    await u.click(within(await renglon("VIV-002")).getByRole("button", { name: "Ver cambios de VIV-002" }));
    const panel = await screen.findByRole("complementary", { name: "Registro de cambios de la versión VIV-002" });
    const registro = await within(panel).findByRole("table", { name: "Registro de cambios de la versión VIV-002" });
    // Pasada de navegador del cierre de F4 (H5): cuándo y quién van primero, como en un registro de auditoría; al final
    // quedaban tras el recorte de la caja (970 px de tabla en 727 a 1366 con letra Normal).
    expect(within(registro).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
      "Fecha y hora",
      "Responsable",
      "Objeto",
      "Clave",
      "Campo",
      "Antes",
      "Después",
      "Fuente",
    ]);
    const r = within(registro).getAllByRole("row")[1]!;
    expect(within(r).getByText("AF-LLAVE, Fuente F1, Fuente FC1, Punto P1, Punto P2, Punto PC1")).toHaveAttribute(
      "title",
      "AF-LLAVE|esp_fuentes:F1;esp_fuentes:FC1;esp_puntos:P1;esp_puntos:P2;esp_puntos:PC1",
    );
    expect(within(r).queryByText(/esp_/)).toBeNull();
    expect(within(r).getByText("Plano revisado en obra")).toBeInTheDocument();
    expect(within(r).getByText("06/10/2026 09:30:00")).toBeInTheDocument();
    expect(fetchFalso.mock.calls.map(([e]) => String(e))).toContain("/v1/hoja/trazabilidad?proyecto=3&version=VIV-002");
    // El panel se cierra con Esc y el foco vuelve al botón que lo abrió.
    await u.keyboard("{Escape}");
    expect(screen.queryByRole("complementary", { name: /Registro de cambios/ })).toBeNull();
    expect(within(await renglon("VIV-002")).getByRole("button", { name: "Ver cambios de VIV-002" })).toHaveFocus();
  });

  test("una versión que no nació de una edición dice por qué no hay registros, sin tabla vacía", async () => {
    const mensaje = "Esta versión no nació de una edición: no tiene registros de cambio.";
    trazabilidad = () => json(trazabilidadRespuesta({ registros: [], vacio_mensaje: mensaje }));
    const u = montar();
    await listo();
    await u.click(within(await renglon("VIV-001")).getByRole("button", { name: "Ver cambios de VIV-001" }));
    const panel = await screen.findByRole("complementary", { name: "Registro de cambios de la versión VIV-001" });
    expect(await within(panel).findByText(mensaje)).toBeInTheDocument();
    expect(within(panel).queryByRole("table")).toBeNull();
  });

  test("lo escrito en el registro va como texto plano, no como Markdown", async () => {
    const registro = { ...trazabilidadRespuesta().registros[0]!, despues: "![x](http://ejemplo.invalid/b.png)" };
    trazabilidad = () => json(trazabilidadRespuesta({ registros: [registro] }));
    const u = montar();
    await listo();
    await u.click(within(await renglon("VIV-002")).getByRole("button", { name: "Ver cambios de VIV-002" }));
    const panel = await screen.findByRole("complementary", { name: "Registro de cambios de la versión VIV-002" });
    expect(await within(panel).findByText("![x](http://ejemplo.invalid/b.png)")).toBeInTheDocument();
    expect(panel.querySelector("img")).toBeNull();
  });
});

describe("Versiones: la franja del paso", () => {
  test("con 3 cambios sin guardar la franja lo dice y su botón abre «Guardar versión»", async () => {
    cambiosAlAbrir = 3;
    const u = montar();
    const franja = await screen.findByRole("region", { name: "Siguiente paso" });
    expect(franja).toHaveTextContent("Siguiente paso: Hay 3 cambios sin guardar");
    const boton = within(franja).getByRole("button", { name: "Guardar versión…" });
    expect(boton).toHaveClass("cds--btn--primary");
    await u.click(boton);
    const dialogo = await screen.findByRole("dialog");
    expect(within(dialogo).getByRole("heading", { name: "Guardar versión" })).toBeInTheDocument();
  });

  test("con la vigente en aprobación dice que espera dictamen, sin botón", async () => {
    aprobaciones = () =>
      json({
        rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." },
        fases: "VIV-002 en aprobación",
        versiones: { "VIV-001": estado("devuelta"), "VIV-002": estado("en_aprobacion") },
        eventos: [],
        ultima_aprobada: null,
      });
    montar();
    const franja = await screen.findByRole("region", { name: "Siguiente paso" });
    await waitFor(() => expect(franja).toHaveTextContent("Siguiente paso: La versión VIV-002 espera dictamen"));
    expect(within(franja).queryByRole("button")).toBeNull();
  });
});

describe("Versiones: la cadena de sellos encima de la tabla", () => {
  test("íntegra: «Integridad verificada» con su ícono y el mensaje del servidor", async () => {
    montar();
    const region = await screen.findByRole("region", { name: "Cadena de sellos" });
    expect(await within(region).findByText("Integridad verificada")).toBeInTheDocument();
    expect(within(region).getByText("Cadena íntegra: 2 versiones")).toBeInTheDocument();
    expect(region.querySelector("svg")).not.toBeNull();
    expect(fetchFalso.mock.calls.map(([e]) => String(e))).toContain("/v1/hoja/cadena?proyecto=3");
  });

  test("rota: «Se rompió en la versión VIV-002» con su ícono", async () => {
    cadena = () => json(CADENA_ROTA);
    montar();
    const region = await screen.findByRole("region", { name: "Cadena de sellos" });
    expect(await within(region).findByText("Se rompió en la versión VIV-002")).toBeInTheDocument();
    expect(within(region).getByText(CADENA_ROTA.mensaje)).toBeInTheDocument();
    expect(region.querySelector("svg")).not.toBeNull(); // el color nunca va solo
    // El aviso va encima de la tabla.
    const t = await tabla();
    expect(region.compareDocumentPosition(t) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  // Mudada de la pestaña «Trazabilidad» de la Hoja con la baja 24 (era «3d-F7: una respuesta de la cadena que no tiene la
  // forma del contrato no se pinta»): pasaba ya allí y aquí fija lo que no debe cambiar.
  test.each([
    ["vacía", () => new Response(null, { status: 204 })],
    ["sin integra", () => json({ mensaje: "x" })],
  ])("una respuesta de la cadena %s no se pinta: lo dice y la tabla sigue", async (_n, respuesta) => {
    cadena = respuesta;
    montar();
    expect(await screen.findByText("La respuesta de la cadena de sellos no tiene la forma esperada.")).toBeInTheDocument();
    expect(await tabla()).toBeInTheDocument();
  });

  test("si la cadena no se puede leer, lo dice sin romper la tabla", async () => {
    cadena = () => json({ detalle: "El proyecto «3» no existe en este caso." }, 404);
    montar();
    expect(await screen.findByText("El proyecto «3» no existe en este caso.")).toBeInTheDocument();
    expect(await tabla()).toBeInTheDocument();
  });
});

describe("Versiones: restaurar", () => {
  test("«Restaurar VIV-001…» abre el diálogo de hoy con la versión elegida, manda proyecto, versión y fuente y abre la nueva", async () => {
    const u = montar();
    await listo();
    fireEvent.click(within(await renglon("VIV-001")).getByRole("button", { name: "Restaurar VIV-001…" }));
    const dialogo = await screen.findByRole("dialog");
    expect(dialogo).toHaveAccessibleName("Restaurar una versión");
    const elegida = within(dialogo).getByRole("combobox", { name: "Versión a restaurar" });
    expect(elegida).toHaveValue("VIV-001");
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Fuente (por qué se restaura)" }), {
      target: { value: "La VIV-002 salió con un error" },
    });
    versiones = {
      ...versiones,
      por_omision: "VIV-003",
      versiones: [fila("VIV-003", "2026-10-22", "restaurada", "VIV-001", true, 0), { ...VIV_002, vigente: false }, VIV_001],
    };
    await u.click(within(dialogo).getByRole("button", { name: "Restaurar" }));
    expect(await screen.findByText("La versión VIV-001 se restauró como la versión VIV-003 (la vigente).")).toBeInTheDocument();
    const restaurados = fetchFalso.mock.calls
      .filter(([e, init]) => String(e) === "/v1/hoja/versiones/restaurar" && init?.method === "POST")
      .map(([, init]) => JSON.parse(String(init?.body)) as unknown);
    expect(restaurados).toEqual([{ proyecto: "3", version: "VIV-001", fuente: "La VIV-002 salió con un error" }]);
    await waitFor(async () => expect((await celdas()).map((c) => c[0])).toEqual(["VIV-003 (abierta)", "VIV-002", "VIV-001"]));
  });

  test("con cambios sin guardar no se ofrece restaurar y se dice por qué", async () => {
    cambiosAlAbrir = 2;
    montar();
    expect(await screen.findByText("Guarde o descarte los cambios pendientes antes de restaurar otra versión.")).toBeInTheDocument();
    await tabla();
    expect(screen.queryByRole("button", { name: /^Restaurar/ })).toBeNull();
  });

  test("con un borrador de solo lectura, quien arma sí restaura (obra sobre la versión guardada) pero no guarda", async () => {
    soloLectura = true;
    montar();
    await listo();
    expect(within(await renglon("VIV-001")).getByRole("button", { name: "Restaurar VIV-001…" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Guardar/ })).toBeNull();
  });
});

// 3e-3 (de la pestaña «Trazabilidad» de la Hoja, que esta sección absorbe; se retiró de `hoja/Versiones.test.tsx` al
// quedarse vacía): el borrador cambia de rev en otra ventana con el diálogo de restaurar abierto. Al volver a la ventana el
// proveedor relee el borrador; ni la página queda `[inert]` ni se pierde el contador de diálogos abiertos.
describe("3e-3: el rev cambia con el diálogo de restaurar abierto (otra ventana) y la página no queda [inert]", () => {
  const hacerQueElServidorTengaOtroRev = (cambios: number) => {
    const previa = fetchFalso.getMockImplementation();
    fetchFalso.mockImplementation(async (entrada, init) => {
      const camino = new URL(String(entrada), "http://silice.local").pathname;
      if (camino === "/v1/hoja/borradores/b-VIV-002" && (init?.method ?? "GET") === "GET") {
        const b = borrador("VIV-002");
        return json({ id: b.id, base: b.base, resumen: { ...b.resumen, rev: 4, cambios } });
      }
      return previa!(entrada, init);
    });
  };
  const volverALaVentana = async () => {
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "visible" });
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
  };
  const abrirRestaurar = async () => {
    fireEvent.click(within(await renglon("VIV-001")).getByRole("button", { name: "Restaurar VIV-001…" }));
    const dialogo = await screen.findByRole("dialog");
    expect(dialogo).toHaveAccessibleName("Restaurar una versión");
    return dialogo;
  };

  test("sin cambios en la otra ventana: el diálogo sigue usable y, al cancelarlo, nada queda inerte", async () => {
    montar();
    await listo();
    await abrirRestaurar();
    expect(document.querySelector("[inert]")).not.toBeNull();
    hacerQueElServidorTengaOtroRev(0);
    await volverALaVentana();
    await waitFor(() =>
      expect(fetchFalso.mock.calls.filter(([e]) => String(e) === "/v1/hoja/borradores/b-VIV-002").length).toBeGreaterThan(0),
    );
    await pausa();
    const dialogo = screen.getByRole("dialog", { name: "Restaurar una versión" });
    expect(dialogo.closest("[inert]")).toBeNull();
    fireEvent.click(within(dialogo).getByRole("button", { name: "Cancelar" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(document.querySelector("[inert]")).toBeNull());
  });

  test("con cambios en la otra ventana: «Restaurar…» se va, el diálogo se cierra con él y nada queda inerte ni se pierde el contador", async () => {
    montar();
    await listo();
    await abrirRestaurar();
    expect(document.querySelector("[inert]")).not.toBeNull();
    hacerQueElServidorTengaOtroRev(2);
    await volverALaVentana();
    expect(await screen.findByText("Guarde o descarte los cambios pendientes antes de restaurar otra versión.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
    await waitFor(() => expect(document.querySelector("[inert]")).toBeNull());
    // la página sigue usable: «Guardar versión…» de la franja abre su diálogo y «Cancelar» la vuelve a dejar libre
    fireEvent.click(screen.getByRole("button", { name: "Guardar versión…" }));
    const otro = await screen.findByRole("dialog");
    expect(otro.closest("[inert]")).toBeNull();
    fireEvent.click(within(otro).getByRole("button", { name: "Cancelar" }));
    await waitFor(() => expect(document.querySelector("[inert]")).toBeNull());
  });
});

describe("Versiones: quien solo revisa (Foco 3)", () => {
  test("ve la tabla con el estado de aprobación, «Abrir» y «Ver cambios», pero no «Restaurar…» ni «Guardar versión…»", async () => {
    aprobaciones = () =>
      json({
        rastro: { integro: true, mensaje: "Rastro de aprobaciones íntegro." },
        fases: "VIV-002 en aprobación",
        versiones: { "VIV-001": estado("devuelta"), "VIV-002": estado("en_aprobacion") },
        eventos: [],
        ultima_aprobada: null,
      });
    montar(REVISA);
    await waitFor(async () => expect((await celdas()).map((c) => c[5])).toEqual(["En aprobación", "Devuelta"]));
    const viv001 = await renglon("VIV-001");
    expect(within(viv001).getByRole("button", { name: "Abrir VIV-001" })).toBeInTheDocument();
    expect(within(viv001).getByRole("button", { name: "Ver cambios de VIV-001" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Restaurar/ })).toBeNull();
    expect(screen.queryByRole("button", { name: /^Guardar/ })).toBeNull();
    const franja = screen.getByRole("region", { name: "Siguiente paso" });
    expect(franja).toHaveTextContent("La versión VIV-002 espera dictamen");
    expect(within(franja).queryByRole("button")).toBeNull();
  });

  test("administrador puro (sin `leer_proyecto`): «Versiones» no aparece en el árbol; quien revisa sí la tiene", () => {
    const deLaObra = (acciones: readonly string[]) => seccionesDeLaObra(ofertaDe(acciones, false)).map((s) => s.id);
    expect(deLaObra(ACCIONES.admin)).not.toContain("versiones");
    expect(deLaObra(ACCIONES.rita)).toContain("versiones");
  });
});

// Ronda 2 de la Tarea 6: el historial solo crece (RF-54). La pestaña «Trazabilidad» (baja 24) listaba todas las versiones y
// su «Restaurar» las ofrecía todas; restaurar es la única manera de deshacer un descarte. VIV-000 es una versión ficticia
// descartada.
describe("Versiones: las descartadas siguen en el historial", () => {
  const VIV_000: VersionFila = { ...fila("VIV-000", "2026-10-19", "", "", false, 0), descartada: true };
  beforeEach(() => {
    versiones = { ...versiones, versiones: [VIV_002, VIV_001, VIV_000] };
  });

  test("la descartada va en la tabla con la palabra «descartada», sin «Abrir», con «Ver cambios» y «Restaurar…»", async () => {
    const u = montar();
    await listo();
    await waitFor(async () =>
      expect((await celdas()).map((c) => c[0])).toEqual(["VIV-002 (abierta)", "VIV-001", "VIV-000 (descartada)"]),
    );
    const viv000 = await renglon("VIV-000");
    expect(within(viv000).queryByRole("button", { name: "Abrir VIV-000" })).toBeNull();
    expect(within(await renglon("VIV-001")).getByRole("button", { name: "Abrir VIV-001" })).toBeInTheDocument();
    expect(within(viv000).getByRole("button", { name: "Restaurar VIV-000…" })).toBeInTheDocument();
    await u.click(within(viv000).getByRole("button", { name: "Ver cambios de VIV-000" }));
    expect(await screen.findByRole("complementary", { name: "Registro de cambios de la versión VIV-000" })).toBeInTheDocument();
    expect(fetchFalso.mock.calls.map(([e]) => String(e))).toContain("/v1/hoja/trazabilidad?proyecto=3&version=VIV-000");
  });

  test("«Restaurar VIV-000…» ofrece todo el historial en el diálogo y manda la descartada", async () => {
    const u = montar();
    await listo();
    await waitFor(async () => expect((await celdas()).map((c) => c[0])).toContain("VIV-000 (descartada)"));
    fireEvent.click(within(await renglon("VIV-000")).getByRole("button", { name: "Restaurar VIV-000…" }));
    const dialogo = await screen.findByRole("dialog");
    const elegida = within(dialogo).getByRole("combobox", { name: "Versión a restaurar" });
    expect(elegida).toHaveValue("VIV-000");
    expect(within(elegida).getAllByRole("option").map((o) => o.textContent)).toEqual(["VIV-002", "VIV-001", "VIV-000"]);
    fireEvent.change(within(dialogo).getByRole("textbox", { name: "Fuente (por qué se restaura)" }), {
      target: { value: "El descarte fue un error" },
    });
    await u.click(within(dialogo).getByRole("button", { name: "Restaurar" }));
    await waitFor(() =>
      expect(
        fetchFalso.mock.calls
          .filter(([e, init]) => String(e) === "/v1/hoja/versiones/restaurar" && init?.method === "POST")
          .map(([, init]) => JSON.parse(String(init?.body)) as unknown),
      ).toEqual([{ proyecto: "3", version: "VIV-000", fuente: "El descarte fue un error" }]),
    );
  });

  test("una cadena rota en la descartada nombra una versión que sí está en la tabla", async () => {
    cadena = () => json({ ...CADENA_ROTA, mensaje: "Cadena rota en la versión VIV-000.", rota_en: "VIV-000" });
    montar();
    const region = await screen.findByRole("region", { name: "Cadena de sellos" });
    expect(await within(region).findByText("Se rompió en la versión VIV-000")).toBeInTheDocument();
    await waitFor(async () => expect((await celdas()).map((c) => c[0])).toContain("VIV-000 (descartada)"));
  });

  test("quien revisa ve la descartada y su «Ver cambios», pero no «Restaurar…» ni «Abrir» (Foco 3)", async () => {
    montar(REVISA);
    await waitFor(async () => expect((await celdas()).map((c) => c[0])).toContain("VIV-000 (descartada)"));
    const viv000 = await renglon("VIV-000");
    expect(within(viv000).getByRole("button", { name: "Ver cambios de VIV-000" })).toBeInTheDocument();
    expect(within(viv000).queryByRole("button", { name: /^Restaurar/ })).toBeNull();
    expect(within(viv000).queryByRole("button", { name: "Abrir VIV-000" })).toBeNull();
  });
});

// Mudada con los archivos (la de 3d-2 de la Hoja los listaba): la interfaz no convierte texto en número.
test("los archivos de Versiones están bajo la prueba estática (sin Number, parseFloat, toFixed ni + unario)", () => {
  const fuentes = import.meta.glob("./*.{ts,tsx}", { query: "?raw", import: "default", eager: true }) as Record<string, string>;
  for (const ruta of ["./index.tsx", "./logica.ts", "./RestaurarVersion.tsx", "./EstadoDeLaCadena.tsx", "./RegistroDeCambios.tsx"]) {
    expect(Object.keys(fuentes), ruta).toContain(ruta);
    expect(fuentes[ruta], ruta).not.toMatch(/\bNumber\s*\(|\bparseFloat\s*\(|\bparseInt\s*\(|\.toFixed\s*\(|(?:[=(,:?]|\breturn)\s*\+\s*[A-Za-z_$(]/);
  }
});
