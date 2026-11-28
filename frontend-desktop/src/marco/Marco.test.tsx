import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useRef, useState } from "react";
import { Link, MemoryRouter, useLocation, useNavigate } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../api/cliente";
import { EsqueletoPagina } from "../comun/EsqueletoPagina";
import type { SesionRespuesta } from "../api/tipos";
import { useAplicacion } from "../shell/contexto";
import { ACCIONES, RUTA_DE_LA_MESA, caso, conLaMesa, estadoInicial, json, ligeras, servidorFalso, sesionDe } from "../shell/obras/datosDePrueba";
import type { EstadoDelServidor } from "../shell/obras/datosDePrueba";
import { RECORRIDO_AUDITAR, iniciarRecorrido, recorridoEnCurso, terminarRecorrido } from "../shell/recorrido";
import { PAGINAS, usable } from "../shell/rutas";
import type { PaginaDef } from "../shell/rutas";
import { cancelarSalida, confirmarSalida } from "../shell/salida";
import { olvidarFormularios, useFormularioSucio } from "../shell/sucio";
import { Marco } from "./Marco";
import { ofertaDe } from "./oferta";
import { crearVigilante, type CanalDeObra } from "./otraPestana";

// Tarea 8 del plan del rediseño del marco: el marco nuevo montado (barra superior, barra lateral, buscador, la obra
// como espacio de trabajo) en vez de los módulos, con lo que seguía vigente del armazón anterior. Oráculos escritos a
// mano: carpetas y obras ficticias, y los textos que fija el plan («Esa obra ya no existe», «Esta obra se abrió en
// otra pestaña», «Retomar»).

const SUR = "Carpeta Sur.db";

// Las obras de cada carpeta (la de la empresa es «silice.db», la de `estadoInicial`).
const OBRAS: Record<string, { id: number; nombre: string; version: string | null; moneda: string }[]> = {
  "silice.db": [
    { id: 7, nombre: "Casa Demo", version: "001", moneda: "Bs" },
    { id: 8, nombre: "Torre B", version: null, moneda: "Bs" },
  ],
  [SUR]: [{ id: 3, nombre: "Galpón Sur", version: "002", moneda: "USD" }],
};

function obrasTodas(estado: EstadoDelServidor) {
  const deLaEmpresa = (c: string) => c === "silice.db";
  return {
    carpeta_actual: deLaEmpresa(estado.actual.nombre) ? null : estado.actual.nombre,
    carpeta_actual_titulo: deLaEmpresa(estado.actual.nombre) ? "Carpeta de la empresa" : estado.actual.nombre.replace(/\.db$/, ""),
    obras: Object.entries(OBRAS).flatMap(([c, lista]) =>
      lista.map((o) => ({
        carpeta: deLaEmpresa(c) ? null : c,
        carpeta_titulo: deLaEmpresa(c) ? "Carpeta de la empresa" : c.replace(/\.db$/, ""),
        obra_id: o.id,
        obra: o.nombre,
        version_codigo: o.version,
      })),
    ),
  };
}

let servidor: ReturnType<typeof servidorFalso>;

function instalar(preparar: (estado: EstadoDelServidor) => void = () => undefined) {
  const estado = estadoInicial();
  estado.casos = [...estado.casos, caso(SUR)];
  preparar(estado);
  servidor = servidorFalso(estado, (metodo, ruta) => {
    if (metodo !== "GET") return undefined;
    if (ruta === "/v1/obras/todas") return json(obrasTodas(estado));
    if (ruta === "/v1/tema") return json({ acento: null, marco: null, lateral: null, tiene_logo: false, avisos: [] });
    if (ruta === "/v1/obras/resumen") {
      const obras = (OBRAS[estado.actual.nombre] ?? []).map((o) => ({ codigo: String(o.id), nombre: o.nombre, moneda: o.moneda }));
      return json({ moneda: "Bs", hoy: "2026-10-27", cifras: [], conversiones: [], fuera_de_suma: [], obras });
    }
    return undefined;
  });
  vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
}

beforeEach(() => {
  instalar();
  fijarCsrf("tok");
});
afterEach(() => {
  cancelarSalida();
  olvidarFormularios();
  terminarRecorrido();
  vi.unstubAllGlobals();
  fijarCsrf(null);
});

// La ruta en que quedó el enrutador (con su consulta).
function Ubicacion() {
  const { pathname, search } = useLocation();
  return <output data-testid="ruta">{`${pathname}${search}`}</output>;
}
const ruta = () => screen.getByTestId("ruta").textContent;

interface Montaje {
  sesion?: SesionRespuesta;
  en?: string;
  paginas?: readonly PaginaDef[];
  canal?: CanalDeObra;
}

function montar({ sesion = sesionDe("ana"), en = "/inicio/pendientes", paginas = ligeras(), canal }: Montaje = {}) {
  const alSalir = vi.fn();
  const alExpirar = vi.fn();
  const vigilante = canal ? crearVigilante(canal) : undefined;
  const vista = render(
    <MemoryRouter initialEntries={[en]}>
      <Marco sesion={sesion} alSalir={alSalir} alExpirar={alExpirar} paginas={paginas} vigilante={vigilante} />
      <Ubicacion />
    </MemoryRouter>,
  );
  return { ...vista, alSalir, alExpirar };
}

const titulo = (nombre: string) => screen.findByRole("heading", { level: 1, name: nombre }, { timeout: 3000 });
const sesionConObra = (proyecto: string) => sesionDe("ana", { eleccion: { caso: null, proyecto, aviso: null } });
const enSur = (estado: EstadoDelServidor) => {
  estado.actual = caso(SUR);
};

// Lo que la instalación apagó (`GET /v1/modulos`): las claves dadas quedan apagadas y el resto encendido.
const MENSAJE_APAGADO = "Esta función está apagada en esta instalación. Quien administra puede encenderla en la Cuenta, sección «Especialidades, IA e instalación».";
function apagar(...claves: string[]) {
  instalar();
  const base = servidor.fetchFalso;
  const nombres: Record<string, string> = { produccion: "producción", vial: "vial", edificacion: "edificación", riesgo: "riesgo" };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (entrada: RequestInfo | URL, init?: RequestInit) => {
      if (String(entrada) === "/v1/modulos" && (init?.method ?? "GET") === "GET") {
        return json({
          modulos: Object.keys(nombres).map((clave) => ({ clave, nombre: nombres[clave], activo: !claves.includes(clave), cambiado_por: null, cambiado_el: null })),
        });
      }
      return base(entrada, init);
    }),
  );
}

describe("Marco: la ruta índice, lo que no existe y las direcciones cortas de la obra", () => {
  // F6, T8 (contrato 1): la ruta índice y lo que no existe llevan a la Vista general.
  test.each(["/", "/inicio", "/no-existe"])("%s acaba en #/inicio/general, la Vista general", async (de) => {
    montar({ en: de });
    expect(await titulo("Vista general")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/general");
  });

  // Contrato §1: toda redirección conserva la consulta.
  test.each([
    ["/?x=1", "la ruta índice"],
    ["/no-existe?x=1", "una ruta que no existe"],
  ])("%s (%s) acaba en la Vista general conservando la consulta", async (de) => {
    montar({ en: de });
    expect(await titulo("Vista general")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/general?x=1");
  });

  test("una pantalla sin definición en el registro lleva a la bandeja conservando la consulta", async () => {
    montar({ en: "/inicio/general?x=1", paginas: ligeras().filter((p) => p.id !== "inicio") });
    expect(await titulo("Pendientes")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/pendientes?x=1");
  });

  // Las direcciones cortas de la obra (`/hoja`, `/reajuste`…) se quedan: son la ruta canónica sin obra (`rutaCanonica`,
  // espacios.ts) que usan el buscador y los recorridos guiados, y llevan a la obra de la sesión (contrato 2.4).
  test("#/hoja con la obra 3 abierta en «Carpeta Sur.db» acaba en su Presupuesto", async () => {
    instalar(enSur);
    montar({ sesion: sesionConObra("3"), en: "/hoja" });
    expect(await titulo("Presupuesto")).toBeInTheDocument();
    expect(ruta()).toBe("/obra/Carpeta%20Sur.db/3/presupuesto");
  });

  test("#/hoja sin obra en la sesión acaba en #/inicio/pendientes", async () => {
    montar({ en: "/hoja" });
    expect(await titulo("Pendientes")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/pendientes");
  });

  test("una sección corta con consulta y sin obra en la sesión se abre donde estaba (no pierde el envío)", async () => {
    montar({ en: "/aprobar?envio=12" });
    expect(await titulo("Aprobar una versión")).toBeInTheDocument();
    expect(ruta()).toBe("/aprobar?envio=12");
  });

  // Contrato 2.4 (enmienda 2026-11-05): la excepción de la consulta vale para secciones y para subvistas de la obra.
  test("una subvista corta con consulta y sin obra en la sesión se abre donde estaba (/reajuste?x=1)", async () => {
    montar({ en: "/reajuste?x=1" });
    expect(await titulo("Reajuste de precios")).toBeInTheDocument();
    expect(ruta()).toBe("/reajuste?x=1");
  });
});

// F8, C1 (contrato 2.4, enmienda 2026-11-06): las direcciones de antes de F6 que llevaban a Pendientes, a un espacio de la
// empresa o a la Cuenta se retiraron. Ya no redirigen a donde vive hoy la pantalla: son direcciones que no existen y, como
// toda dirección inexistente, llevan a la Vista general conservando la consulta. Tabla escrita a mano desde el contrato:
// la dirección vieja y adónde llevaba antes.
describe("Marco: las direcciones viejas se retiraron (F8, C1)", () => {
  const RETIRADAS: readonly (readonly [string, string])[] = [
    ["/pendientes", "/inicio/pendientes"],
    ["/existencias", "/produccion/existencias"],
    ["/costos", "/produccion/costos"],
    ["/costo_tonelada", "/produccion/costo-tonelada"],
    ["/receta_planta", "/produccion/receta"],
    ["/producir_mezcla", "/produccion/mezcla"],
    ["/libros", "/auditoria/libros"],
    ["/historial", "/auditoria/historial"],
    ["/precios_empresa", "/precios/listas"],
    ["/catalogo", "/precios/catalogo"],
    ["/indices", "/precios/indices"],
    ["/simulador", "/precios/simulador"],
    ["/empresa/precios", "/precios/catalogo"],
    ["/empresa/auditoria", "/auditoria/subir"],
    ["/empresa/produccion", "/produccion/existencias"],
    ["/empresa/personas", "/cuenta/cuentas"],
    ["/empresa/ayuda", "/cuenta/ayuda"],
    ["/administracion", "/cuenta/cuentas"],
    ["/acerca", "/cuenta/ayuda"],
  ];

  test.each(RETIRADAS)("%s ya no lleva a %s: acaba en la Vista general", async (de) => {
    montar({ sesion: sesionDe("admin"), en: de });
    expect(await titulo("Vista general")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/general");
  });

  test.each(RETIRADAS)("%s?proyecto=OF-001 acaba en la Vista general con su consulta", async (de) => {
    montar({ en: `${de}?proyecto=OF-001` });
    expect(await titulo("Vista general")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/general?proyecto=OF-001");
  });

  test("una entrada de Empresa que nunca existió también acaba en la Vista general", async () => {
    montar({ en: "/empresa/xyz" });
    expect(await titulo("Vista general")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/general");
  });

  // Contrato 1 («espacio sin herramienta»): `/produccion` y `/auditoria` no son direcciones viejas, sino la raíz de su espacio.
  test.each([
    ["/produccion", "/produccion/resumen"],
    ["/auditoria", "/auditoria/subir"],
    ["/auditoria?x=1", "/auditoria/subir?x=1"],
  ])("%s sigue abriendo su espacio: %s", async (de, a) => {
    montar({ en: de });
    await waitFor(() => expect(ruta()).toBe(a));
  });
});

// F6, T4: Producción, Auditoría y Precios son espacios con su barra de herramientas (/<espacio>/<herramienta>).
describe("Marco: los espacios de Producción, Auditoría y Precios (F6, T4)", () => {
  // Reestructuración, lote C4 (decisión de Eugenio, 2026-11-26): los espacios de la empresa viven en la barra lateral, que se
  // ve también dentro de ellos. Por eso ya no hay «Volver a obras» ni el selector de herramientas dedicadas en la barra de
  // arriba: la lateral es la que lleva de un espacio a otro y a cada obra.
  test("#/precios/simulador se abre con la barra lateral (espacios y obras), sin «Volver a obras» arriba", async () => {
    montar({ en: "/precios/simulador" });
    expect(await titulo("Simulador de listas")).toBeInTheDocument();
    expect(ruta()).toBe("/precios/simulador");
    const barra = screen.getByRole("banner");
    expect(within(barra).getByRole("button", { name: "Buscar una obra, sección o pantalla… (Ctrl+K)" })).toBeInTheDocument();
    expect(within(barra).queryByRole("link", { name: "Volver a obras" })).toBeNull();
    const lateral = screen.getByRole("complementary", { name: "Barra lateral" });
    expect(within(lateral).getByRole("link", { name: "Precios y catálogo" })).toHaveAttribute("aria-current", "page");
    expect(within(lateral).getByRole("link", { name: "Inicio" })).toBeInTheDocument();
    expect(within(barra).queryByRole("navigation", { name: "Ruta" })).toBeNull();
    expect(within(screen.getByRole("navigation", { name: "Precios y catálogo" })).getByRole("link", { name: "Simulador de listas" })).toHaveAttribute("aria-current", "page");
  });

  test("las cuentas, para quien no administra, dicen en la Cuenta que no tiene permiso", async () => {
    montar({ en: "/cuenta/cuentas" });
    expect(await screen.findByText("Su cuenta no tiene permiso para esta pantalla o acción.")).toBeInTheDocument();
    expect(ruta()).toBe("/cuenta/cuentas");
  });

  test("quien arma entra a #/precios por el Catálogo y el administrador, por los precios de la empresa", async () => {
    const arma = montar({ sesion: sesionDe("ana"), en: "/precios" });
    expect(await titulo("Catálogo de partidas e insumos")).toBeInTheDocument();
    expect(ruta()).toBe("/precios/catalogo");
    arma.unmount();
    montar({ sesion: sesionDe("admin"), en: "/precios" });
    expect(await titulo("Precios de la empresa")).toBeInTheDocument();
    expect(ruta()).toBe("/precios/listas");
  });

  test("una herramienta que no existe lleva a la primera usable, con replace y conservando la consulta", async () => {
    montar({ sesion: sesionDe("ana"), en: "/precios/xyz?proyecto=OF-001" });
    expect(await titulo("Catálogo de partidas e insumos")).toBeInTheDocument();
    expect(ruta()).toBe("/precios/catalogo?proyecto=OF-001");
  });

  test("#/auditoria/xyz y #/produccion/xyz también", async () => {
    const a = montar({ en: "/auditoria/xyz" });
    await waitFor(() => expect(ruta()).toBe("/auditoria/subir"));
    a.unmount();
    montar({ en: "/produccion/xyz" });
    await waitFor(() => expect(ruta()).toBe("/produccion/resumen"));
  });

  test("la pantalla tiene un solo h1 y las cabeceras y barras del espacio no lo suman", async () => {
    montar({ en: "/produccion/existencias" });
    expect(await titulo("Existencias de la arenera")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    // Lote C4: el espacio tiene UNA barra de lugar de dos filas: su nombre arriba (sin ser un encabezado) y sus herramientas debajo.
    const barra = screen.getByRole("navigation", { name: "Costos de producción" });
    const doble = barra.closest(".silice-barra-espacio-doble") as HTMLElement;
    expect(doble).not.toBeNull();
    expect(screen.queryByRole("region", { name: "Costos de producción" })).toBeNull();
    expect(within(doble).queryByRole("heading")).toBeNull();
    const nombre = within(doble).getByText("Costos de producción");
    // El nombre va arriba de las herramientas y la barra, arriba de la pantalla.
    expect(nombre.compareDocumentPosition(barra) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(barra.compareDocumentPosition(screen.getByRole("heading", { level: 1 })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  test("la barra ofrece las herramientas que la cuenta puede usar, en el orden de la tabla, con la actual marcada", async () => {
    montar({ sesion: sesionDe("ana"), en: "/precios/catalogo" });
    await titulo("Catálogo de partidas e insumos");
    const barra = screen.getByRole("navigation", { name: "Precios y catálogo" });
    // Ana no administra precios: ni los precios de la empresa ni los índices; sí edita la hoja (el simulador).
    expect(within(barra).getAllByRole("link").map((e) => [e.textContent, e.getAttribute("href")])).toEqual([
      ["Catálogo de partidas e insumos", "/precios/catalogo"],
      ["Simulador de listas", "/precios/simulador"],
    ]);
    expect(within(barra).getByRole("link", { name: "Catálogo de partidas e insumos" })).toHaveAttribute("aria-current", "page");
  });

  test("«Sin permiso»: una herramienta que la cuenta no puede usar, escrita a mano, lo dice y la barra sigue", async () => {
    const sinCostos = sesionDe("ana", { acciones: ACCIONES.ana.filter((a) => a !== "registrar_costos_produccion") });
    montar({ sesion: sinCostos, en: "/produccion/costos" });
    expect(await screen.findByText("Sin permiso")).toBeInTheDocument();
    expect(screen.getByText("Su cuenta no tiene permiso para esta pantalla o acción.")).toBeInTheDocument();
    expect(ruta()).toBe("/produccion/costos");
    const barra = screen.getByRole("navigation", { name: "Costos de producción" });
    expect(within(barra).queryByRole("link", { name: "Costos del período" })).toBeNull();
    expect(within(barra).getByRole("link", { name: "Existencias" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1, name: "Costos del período" })).toBeNull();
  });

  test("sin ninguna herramienta usable el espacio abre la primera definida con el aviso, sin bucle y sin barra vacía", async () => {
    montar({ sesion: sesionDe("rita"), en: "/produccion" });
    expect(await screen.findByText("Sin permiso")).toBeInTheDocument();
    expect(ruta()).toBe("/produccion/resumen");
    expect(screen.queryByRole("navigation", { name: "Costos de producción" })).toBeNull();
    // El aviso es el único h1 de la pantalla (pasada en el navegador, H9): sin él la página quedaba sin título.
    expect(screen.getAllByRole("heading", { level: 1 })).toEqual([screen.getByRole("heading", { level: 1, name: "Sin permiso" })]);
  });

  test("cambiar de herramienta desde la barra deja el foco en el enlace pulsado (la barra no se vuelve a montar)", async () => {
    const u = userEvent.setup();
    montar({ en: "/produccion/existencias" });
    await titulo("Existencias de la arenera");
    const barra = screen.getByRole("navigation", { name: "Costos de producción" });
    const enlace = within(barra).getByRole("link", { name: "Costos del período" });
    await u.click(enlace);
    expect(await titulo("Costos del período")).toBeInTheDocument();
    expect(ruta()).toBe("/produccion/costos");
    const despues = within(screen.getByRole("navigation", { name: "Costos de producción" })).getByRole("link", { name: "Costos del período" });
    expect(despues).toBe(enlace);
    expect(despues).toHaveFocus();
    expect(despues).toHaveAttribute("aria-current", "page");
  });

  test("document.title dice la herramienta y el espacio", async () => {
    montar({ en: "/produccion/costos" });
    await titulo("Costos del período");
    expect(document.title).toBe("Costos del período · Costos de producción · Sílice");
  });

  test("la barra de arriba no tiene migas: el espacio y la herramienta los dicen su cabecera y su barra", async () => {
    montar({ en: "/auditoria/libros" });
    await titulo("Libro de la empresa");
    expect(screen.queryByRole("navigation", { name: "Ruta" })).toBeNull();
    const barra = screen.getByRole("navigation", { name: "Auditar un presupuesto" });
    expect(within(barra).getByRole("link", { name: "Libro de la empresa" })).toHaveAttribute("aria-current", "page");
  });

  // Antes el selector superior de «herramientas dedicadas» marcaba el espacio abierto; ya no existe (los espacios van en la
  // barra lateral, decisión de Eugenio 2026-11-26): ahora lo marca la lateral y arriba no queda ningún selector.
  test("dentro de un espacio la barra lateral marca ese espacio y arriba no hay selector de herramientas dedicadas", async () => {
    montar({ en: "/auditoria/historial" });
    await titulo("Historial de auditorías");
    expect(screen.queryByRole("navigation", { name: "Selector de herramientas dedicadas" })).toBeNull();
    const lateral = screen.getByRole("complementary", { name: "Barra lateral" });
    expect(within(lateral).getByRole("link", { name: "Auditar un presupuesto" })).toHaveAttribute("aria-current", "page");
    expect(within(lateral).getByRole("link", { name: "Costos de producción" })).not.toHaveAttribute("aria-current");
  });

  test("Ctrl+K lleva a las rutas nuevas", async () => {
    const u = userEvent.setup();
    montar({ en: "/inicio/pendientes" });
    await titulo("Pendientes");
    await u.keyboard("{Control>}k{/Control}");
    await u.type(screen.getByRole("combobox", { name: "Buscar una obra, sección o pantalla" }), "existencias");
    await u.keyboard("{Enter}");
    await waitFor(() => expect(ruta()).toBe("/produccion/existencias"));
  });
});

// Una pantalla que solo se monta con su módulo encendido (Series del riesgo vial) no puede tomar «todavía no se leyó» por
// «ninguno apagado»: el marco le da `undefined` hasta que vuelve `GET /v1/modulos` y la lista después.
describe("Marco: los módulos apagados que ve una pantalla", () => {
  function PaginaDeModulos() {
    const { modulosApagados } = useAplicacion();
    return (
      <>
        <h1>Presupuesto</h1>
        <p>{`módulos: ${modulosApagados === undefined ? "sin leer" : modulosApagados.join(", ") || "ninguno apagado"}`}</p>
      </>
    );
  }

  test("mientras la lectura va en vuelo la pantalla ve undefined y al resolver ve la lista", async () => {
    instalar(enSur);
    const base = servidor.fetchFalso;
    let contestar: (r: Response) => void = () => undefined;
    const retenida = new Promise<Response>((resolver) => (contestar = resolver));
    vi.stubGlobal(
      "fetch",
      vi.fn(async (entrada: RequestInfo | URL, init?: RequestInit) => {
        if (String(entrada) === "/v1/modulos" && (init?.method ?? "GET") === "GET") return retenida;
        return base(entrada, init);
      }),
    );
    montar({ en: "/obra/Carpeta%20Sur.db/3/presupuesto", paginas: ligeras({ hoja: PaginaDeModulos }) });
    expect(await screen.findByText("módulos: sin leer")).toBeInTheDocument();
    await act(async () => {
      contestar(json({ modulos: [{ clave: "riesgo", nombre: "riesgo", activo: false, cambiado_por: null, cambiado_el: null }] }));
    });
    expect(await screen.findByText("módulos: riesgo")).toBeInTheDocument();
  });
});

describe("Marco: la obra como espacio de trabajo", () => {
  function PaginaConObra() {
    const { proyecto, nombreProyecto } = useAplicacion();
    return (
      <>
        <h1>Presupuesto</h1>
        <p>{`obra de la página: ${proyecto ?? "ninguna"} (${nombreProyecto ?? "?"})`}</p>
      </>
    );
  }

  test("dentro de una sección se ve la cabecera de la obra (nombre, moneda, versión), la carpeta activa y la página", async () => {
    instalar((estado) => {
      enSur(estado);
      estado.moneda = "USD";
    });
    montar({ en: "/obra/Carpeta%20Sur.db/3/presupuesto", paginas: ligeras({ hoja: PaginaConObra }) });
    expect(await titulo("Presupuesto")).toBeInTheDocument();
    expect(screen.getByText("obra de la página: 3 (Galpón Sur)")).toBeInTheDocument();
    const cabecera = screen.getByRole("region", { name: "Obra abierta" });
    expect(within(cabecera).getByText("Galpón Sur")).toBeInTheDocument();
    await waitFor(() => expect(cabecera).toHaveTextContent("Moneda: USD"));
    // La moneda se dice una sola vez, sin «de trabajo».
    expect(cabecera.textContent?.match(/moneda/gi)).toHaveLength(1);
    expect(cabecera).not.toHaveTextContent("de trabajo");
    expect(cabecera).toHaveTextContent("Versión: 002");
    expect(screen.queryByRole("navigation", { name: "Ruta" })).toBeNull();
    // El rótulo y el nombre van en dos partes (con letra grande el rótulo se oculta a la vista); la frase sigue entera.
    expect(await screen.findByTitle("Carpeta activa: Carpeta Sur")).toHaveTextContent("Carpeta activa: Carpeta Sur");
    expect(await screen.findByText("Obras / Galpón Sur")).toBeInTheDocument();
    expect(document.title).toBe("Presupuesto · Galpón Sur · Sílice");
  });

  // F4, Tarea 3: el espacio de la obra no se vuelve a montar al cambiar de sección (el borrador de la Hoja vive en él). La
  // ficha se lee una vez por entrada al Resumen (ronda 2: lo que cambió desde Presupuesto, Aprobaciones o Control se ve).
  test("cambiar de sección dentro de la misma obra no vuelve a fijar la obra; la ficha se lee al entrar al Resumen", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/resumen" });
    expect(await titulo("Resumen de la obra")).toBeInTheDocument();
    await waitFor(() => expect(servidor.de("GET", "/v1/obras/resumen")).toHaveLength(1));
    expect(servidor.de("PUT", "/v1/sesion/proyecto")).toHaveLength(1);
    // Una sola barra de lugar: las herramientas arriba y, debajo, las opciones de la herramienta abierta (Mercado es una opción de Presupuestar).
    const herramientas = await screen.findByRole("navigation", { name: "Herramientas de la obra" });
    await u.click(within(herramientas).getByRole("link", { name: "Presupuestar" }));
    expect(await titulo("Presupuesto")).toBeInTheDocument();
    await u.click(await within(await screen.findByRole("navigation", { name: "Opciones de Presupuestar" })).findByRole("link", { name: "Precios de mercado" }));
    expect(await titulo("Estudio de mercado")).toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 30));
    expect({
      fijadas: servidor.de("PUT", "/v1/sesion/proyecto").length,
      fichas: servidor.de("GET", "/v1/obras/resumen").length,
    }).toEqual({ fijadas: 1, fichas: 1 });
    await u.click(within(screen.getByRole("region", { name: "Obra abierta" })).getByRole("link", { name: /Portada de la obra/ }));
    expect(await titulo("Resumen de la obra")).toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 30));
    expect({
      fijadas: servidor.de("PUT", "/v1/sesion/proyecto").length,
      fichas: servidor.de("GET", "/v1/obras/resumen").length,
    }).toEqual({ fijadas: 1, fichas: 2 });
  });

  test("una obra sin versión guardada lo dice en la cabecera", async () => {
    montar({ en: "/obra/empresa/8/presupuesto" });
    expect(await titulo("Presupuesto")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Obra abierta" })).toHaveTextContent("Versión: sin versión guardada");
  });

  test("si otra pestaña abre otra obra, esta dice «Esta obra se abrió en otra pestaña», no monta la página y «Retomar» vuelve", async () => {
    const u = userEvent.setup();
    const canal: CanalDeObra = { onmessage: null, postMessage: vi.fn() };
    montar({ en: "/obra/empresa/7/presupuesto", canal });
    expect(await titulo("Presupuesto")).toBeInTheDocument();
    const fijadas = servidor.de("PUT", "/v1/sesion/proyecto").length;
    canal.onmessage?.({ data: { carpeta: SUR, obraId: 3 } } as MessageEvent);
    expect(await titulo("Esta obra se abrió en otra pestaña")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1, name: "Presupuesto" })).toBeNull();
    await u.click(screen.getByRole("button", { name: "Retomar" }));
    expect(await titulo("Presupuesto")).toBeInTheDocument();
    expect(servidor.de("PUT", "/v1/sesion/proyecto").length).toBe(fijadas + 1);
  });

  test("un enlace viejo a una obra borrada dice «Esa obra ya no existe» con un enlace a Pendientes", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/99/resumen" });
    expect(await titulo("Esa obra ya no existe")).toBeInTheDocument();
    await u.click(screen.getByRole("link", { name: "Volver a Pendientes" }));
    expect(await titulo("Pendientes")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/pendientes");
  });

  // Rediseño F3, Tarea 2: Pendientes ya no monta la mesa (es la bandeja, que no muestra la obra elegida); se sigue por
  // Pendientes hasta una entrada de Empresa, otra pantalla de fuera de la obra.
  test("la obra en que se entró queda elegida para las pantallas de fuera de la obra (Pendientes y Empresa)", async () => {
    const u = userEvent.setup();
    function ConLaObra() {
      const { proyecto } = useAplicacion();
      return (
        <>
          <h1>Con la obra</h1>
          <p>{`obra elegida: ${proyecto ?? "ninguna"}`}</p>
        </>
      );
    }
    montar({ en: "/obra/empresa/7/resumen", paginas: ligeras({ obras: ConLaObra, catalogo: ConLaObra }) });
    expect(await screen.findByText("obra elegida: 7")).toBeInTheDocument();
    await u.click(within(screen.getByRole("complementary", { name: "Barra lateral" })).getByRole("link", { name: "Inicio" }));
    await waitFor(() => expect(ruta()).toBe("/inicio/general"));
    expect(await titulo("Vista general")).toBeInTheDocument();
    await u.click(within(screen.getByRole("complementary", { name: "Barra lateral" })).getByRole("link", { name: "Precios y catálogo" }));
    await waitFor(() => expect(ruta()).toBe("/precios/catalogo"));
    expect(await screen.findByText("obra elegida: 7")).toBeInTheDocument();
  });
});

// F6, T5: la obra con su barra de secciones bajo la cabecera, las subvistas dentro de su sección y la barra lateral plana.
// Contrato de rutas 2.1 y 2.4 y diseño visual (2.2 y adenda A): oráculos escritos a mano.
describe("Marco: la barra de la obra y las subvistas (F6, T5)", () => {
  // Reestructuración, lote C4: una obra tiene UNA sola barra de lugar (la de BarraDeObra, que monta la cabecera): arriba su
  // nombre (la Portada), las tres herramientas y el menú «Versión»; debajo, las opciones de la herramienta abierta. La barra de
  // «Secciones de la obra» de la cara anterior ya no existe: sus nueve secciones se reparten entre esas herramientas y opciones.
  const herramientasDeLaObra = () => screen.getByRole("navigation", { name: "Herramientas de la obra" });
  const opcionesDe = (herramienta: string) => screen.getByRole("navigation", { name: `Opciones de ${herramienta}` });
  const textos = (nav: HTMLElement) => within(nav).getAllByRole("link").map((e) => e.textContent);
  const actuales = (nav: HTMLElement) => within(nav).getAllByRole("link").filter((e) => e.getAttribute("aria-current") === "page").map((e) => e.textContent);
  const SEGUIDO = Node.DOCUMENT_POSITION_FOLLOWING;

  test("la obra tiene una sola barra de lugar, dentro de la cabecera: tres herramientas y, debajo, las opciones de la abierta", async () => {
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    const cabecera = screen.getByRole("region", { name: "Obra abierta" });
    expect(screen.queryByRole("navigation", { name: "Secciones de la obra" })).toBeNull();
    const herramientas = herramientasDeLaObra();
    const opciones = opcionesDe("Presupuestar");
    expect(cabecera).toContainElement(herramientas);
    expect(cabecera).toContainElement(opciones);
    expect(herramientas.compareDocumentPosition(opciones) & SEGUIDO).toBeTruthy();
    expect(cabecera.compareDocumentPosition(screen.getByRole("heading", { level: 1 })) & SEGUIDO).toBeTruthy();
    expect(cabecera.closest("main")).not.toBeNull();
    expect(textos(herramientas)).toEqual(["Presupuestar", "Auditar", "Anticipar"]);
    expect(within(herramientas).getAllByRole("link").map((e) => e.getAttribute("href"))).toEqual(
      ["presupuesto", "aprobaciones", "control"].map((s) => `/obra/empresa/7/${s}`),
    );
    expect(actuales(herramientas)).toEqual(["Presupuestar"]);
    expect(textos(opciones)).toEqual(["Partidas", "Componer un APU", "Espacio, plan y ajustes", "Tramos de la vía", "Plano o cómputo", "Precios de mercado"]);
    expect(within(opciones).getAllByRole("link").map((e) => e.getAttribute("href"))).toEqual(
      ["presupuesto", "presupuesto/componer", "presupuesto/pestanas", "tramos", "archivos", "mercado"].map((s) => `/obra/empresa/7/${s}`),
    );
    expect(actuales(opciones)).toEqual(["Partidas"]);
    expect(within(cabecera).queryByRole("heading")).toBeNull();
  });

  // Prueba en vivo (2026-11-18): una sección inexistente de una obra que SÍ existe decía «Esa obra ya no existe. La
  // borraron…», que es falso. Como una subvista desconocida, lleva a la pantalla principal (el Resumen), con replace y la consulta.
  test("una sección inexistente de una obra que existe lleva al Resumen de la obra, con replace y la consulta", async () => {
    montar({ en: "/obra/empresa/7/no-existe?x=1" });
    expect(await titulo("Resumen de la obra")).toBeInTheDocument();
    expect(ruta()).toBe("/obra/empresa/7/resumen?x=1");
    expect(screen.queryByText("Esa obra ya no existe")).toBeNull();
  });

  test("una sección inexistente de una obra que tampoco existe sigue diciendo que la obra no existe", async () => {
    montar({ en: "/obra/empresa/99/no-existe" });
    expect(await titulo("Esa obra ya no existe")).toBeInTheDocument();
  });

  test("una sección inexistente con un número de obra que no es entero seguro no redirige: la obra no existe", async () => {
    montar({ en: "/obra/empresa/99999999999999999999/no-existe" });
    expect(await titulo("Esa obra ya no existe")).toBeInTheDocument();
    expect(ruta()).toBe("/obra/empresa/99999999999999999999/no-existe");
  });

  test("sin la obra lista (una que no existe) no hay cabecera ni barra de la obra", async () => {
    montar({ en: "/obra/empresa/99/resumen" });
    await titulo("Esa obra ya no existe");
    expect(screen.queryByRole("navigation", { name: "Herramientas de la obra" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Obra abierta" })).toBeNull();
  });

  test("quien solo revisa ve las herramientas y opciones que puede usar (sin Tramos ni Control de obra)", async () => {
    montar({ sesion: sesionDe("rita"), en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    expect(textos(herramientasDeLaObra())).toEqual(["Presupuestar", "Auditar", "Anticipar"]);
    expect(textos(opcionesDe("Presupuestar"))).not.toContain("Tramos de la vía");
    expect(textos(opcionesDe("Presupuestar"))).toEqual(expect.arrayContaining(["Plano o cómputo", "Precios de mercado"]));
    // Anticipar, para quien solo revisa, lleva a Riesgo: Control de obra no es suyo.
    expect(within(herramientasDeLaObra()).getByRole("link", { name: "Anticipar" })).toHaveAttribute("href", "/obra/empresa/7/riesgo");
  });

  test("Riesgo solo se ofrece con su especialidad encendida", async () => {
    const encendida = montar({ en: "/obra/empresa/7/control" });
    await titulo("Control de obra");
    expect(textos(opcionesDe("Anticipar"))).toContain("Riesgo");
    encendida.unmount();
    apagar("riesgo");
    montar({ en: "/obra/empresa/7/control" });
    await titulo("Control de obra");
    await waitFor(() => expect(textos(opcionesDe("Anticipar"))).not.toContain("Riesgo"));
    expect(textos(opcionesDe("Anticipar"))).toEqual(["Control de obra", "Reajuste de precios", "Escenarios"]);
  });

  test("Tramos sigue la especialidad vial: apagada, la opción no se ofrece", async () => {
    apagar("vial");
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    await waitFor(() => expect(textos(opcionesDe("Presupuestar"))).not.toContain("Tramos de la vía"));
  });

  test("las secciones de la obra ya no cuelgan de la barra lateral", async () => {
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    const lateral = screen.getByRole("complementary", { name: "Barra lateral" });
    for (const seccion of ["Presupuesto", "Versiones", "Control de obra", "Archivos y planos"]) {
      expect(within(lateral).queryByRole("link", { name: seccion })).toBeNull();
    }
    expect(lateral.querySelector('[role="tree"], [role="treeitem"], [aria-expanded="true"][aria-level]')).toBeNull();
  });

  test("/obra/empresa/7/control/reajuste monta Reajuste: «Control de obra» activa en la barra de la obra y «Reajuste» en el conmutador", async () => {
    montar({ en: "/obra/empresa/7/control/reajuste" });
    expect(await titulo("Reajuste de precios")).toBeInTheDocument();
    expect(ruta()).toBe("/obra/empresa/7/control/reajuste");
    expect(actuales(herramientasDeLaObra())).toEqual(["Anticipar"]);
    expect(actuales(opcionesDe("Anticipar"))).toEqual(["Reajuste de precios"]);
    // Integración C3-C5: las subvistas son opciones de la segunda fila de la obra; ya no hay conmutador aparte.
    expect(screen.queryByRole("navigation", { name: "Vistas de Control de obra" })).toBeNull();
    const fila = opcionesDe("Anticipar");
    expect(within(fila).getAllByRole("link").map((e) => [e.textContent, e.getAttribute("href"), e.getAttribute("aria-current")])).toEqual([
      ["Control de obra", "/obra/empresa/7/control", null],
      ["Reajuste de precios", "/obra/empresa/7/control/reajuste", "page"],
      ["Escenarios", "/obra/empresa/7/control/escenarios", null],
      ["Riesgo", "/obra/empresa/7/riesgo", null],
    ]);
    // La segunda fila va encima de la pantalla y no pone h1.
    expect(fila.compareDocumentPosition(screen.getByRole("heading", { level: 1 })) & SEGUIDO).toBeTruthy();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(within(fila).queryByRole("heading")).toBeNull();
  });

  test("en la pantalla principal de la sección el conmutador marca su raíz (Resumen y Tablero)", async () => {
    montar({ en: "/obra/empresa/7/resumen" });
    await titulo("Resumen de la obra");
    // Integración C3-C5: Resumen y Tablero son las opciones de la portada, en la segunda fila de la obra.
    const conmutador = opcionesDe("la portada");
    expect(within(conmutador).getAllByRole("link").map((e) => [e.textContent, e.getAttribute("aria-current")])).toEqual([
      ["Resumen", "page"],
      ["Tablero", null],
    ]);
  });

  test.each([
    // Integración C3-C5: Presupuesto y Aprobaciones se eligen en la segunda fila de la obra; Mercado conserva su conmutador
    // porque «Actualizar precios» no es una opción de la fila.
    ["Opciones de Presupuestar", ["Partidas", "Componer un APU", "Espacio, plan y ajustes", "Tramos de la vía", "Plano o cómputo", "Precios de mercado"], "/obra/empresa/7/presupuesto"],
    ["Opciones de Auditar", ["Aprobar", "Revisar un paquete", "Entregar"], "/obra/empresa/7/aprobaciones"],
    ["Vistas de Mercado", ["Estudio", "Actualizar precios"], "/obra/empresa/7/mercado"],
  ])("%s ofrece %j para quien puede usarlas todas", async (nombre, esperadas, en) => {
    const todo = sesionDe("ana", { acciones: [...ACCIONES.ana, "revisar_paquete"] });
    montar({ sesion: todo, en });
    await screen.findByRole("heading", { level: 1 });
    expect(textos(screen.getByRole("navigation", { name: nombre }))).toEqual(esperadas);
  });

  test("con una sola vista usable no se pinta el conmutador (rita no edita la hoja: Presupuesto queda con su vista principal)", async () => {
    montar({ sesion: sesionDe("rita"), en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    expect(screen.queryByRole("navigation", { name: "Vistas de Presupuesto" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Componer" })).toBeNull();
  });

  // B1-10: las pestañas de antes son la subvista «Espacio, plan y ajustes», una opción más de la segunda fila de la obra;
  // quien solo revisa también la ve (en solo lectura).
  test("«Espacio, plan y ajustes» es una opción de Presupuestar que lleva a la subvista de las pestañas", async () => {
    const u = userEvent.setup();
    montar({ sesion: sesionDe("rita"), en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    const enlace = within(opcionesDe("Presupuestar")).getByRole("link", { name: "Espacio, plan y ajustes" });
    expect(enlace).toHaveAttribute("href", "/obra/empresa/7/presupuesto/pestanas");
    await u.click(enlace);
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/presupuesto/pestanas"));
    expect(await titulo("Espacio, plan y ajustes")).toBeInTheDocument();
  });

  test("las secciones sin subvistas no tienen conmutador", async () => {
    montar({ en: "/obra/empresa/7/versiones" });
    await titulo("Versiones");
    expect(screen.queryByRole("navigation", { name: /^Vistas de/ })).toBeNull();
  });

  test("una sección cuya pantalla principal no es usable abre su primera subvista usable, conservando la consulta", async () => {
    const quienRevisa = sesionDe("rita", { acciones: ["leer_proyecto", "revisar_paquete"] });
    montar({ sesion: quienRevisa, en: "/obra/empresa/7/aprobaciones?x=1" });
    expect(await titulo("Revisar un paquete")).toBeInTheDocument();
    expect(ruta()).toBe("/obra/empresa/7/aprobaciones/revisar?x=1");
    // Bajo la herramienta «Auditar» de la obra; con una sola vista usable no hay conmutador.
    expect(actuales(herramientasDeLaObra())).toEqual(["Auditar"]);
    expect(actuales(opcionesDe("Auditar"))).toEqual(["Revisar un paquete"]);
    expect(screen.queryByRole("navigation", { name: "Vistas de Aprobaciones" })).toBeNull();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  test("una subvista desconocida lleva a la pantalla principal de la sección, con replace y la consulta", async () => {
    montar({ en: "/obra/empresa/7/control/xyz?a=1" });
    expect(await titulo("Control de obra")).toBeInTheDocument();
    expect(ruta()).toBe("/obra/empresa/7/control?a=1");
  });

  test.each([
    ["/obra/empresa/7/versiones/xyz", "/obra/empresa/7/versiones", "Versiones"],
    ["/obra/empresa/7/resumen/reajuste", "/obra/empresa/7/resumen", "Resumen de la obra"],
    ["/obra/empresa/7/riesgo/componer", "/obra/empresa/7/riesgo", "Riesgo de la obra"],
  ])("%s acaba en %s", async (de, a, h1) => {
    montar({ en: de });
    expect(await titulo(h1)).toBeInTheDocument();
    expect(ruta()).toBe(a);
  });

  test("una subvista que la cuenta no puede usar, escrita a mano, dice «Sin permiso» y la barra sigue", async () => {
    montar({ sesion: sesionDe("rita"), en: "/obra/empresa/7/control/reajuste" });
    expect(await screen.findByText("Sin permiso")).toBeInTheDocument();
    expect(ruta()).toBe("/obra/empresa/7/control/reajuste");
    expect(screen.queryByRole("heading", { level: 1, name: "Reajuste de precios" })).toBeNull();
    // Dentro de la obra, con su cabecera encima, el aviso sigue siendo el único h1 (H9).
    expect(screen.getAllByRole("heading", { level: 1 })).toEqual([screen.getByRole("heading", { level: 1, name: "Sin permiso" })]);
    expect(within(herramientasDeLaObra()).getByRole("link", { name: "Presupuestar" })).toBeInTheDocument();
  });

  test("el título del documento y la barra de vistas dicen la subvista", async () => {
    montar({ en: "/obra/empresa/7/control/reajuste" });
    await titulo("Reajuste de precios");
    expect(document.title).toBe("Reajuste · Control de obra · Casa Demo · Sílice");
    const vistas = within(screen.getByRole("navigation", { name: "Opciones de Anticipar" }));
    expect(vistas.getByRole("link", { name: "Reajuste de precios" })).toHaveAttribute("aria-current", "page");
    expect(vistas.getByRole("link", { name: "Control de obra" })).toHaveAttribute("href", "/obra/empresa/7/control");
  });

  test("cambiar de subvista con el conmutador deja el foco en el enlace pulsado (no se vuelve a montar)", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/control/reajuste" });
    await titulo("Reajuste de precios");
    const enlace = within(screen.getByRole("navigation", { name: "Opciones de Anticipar" })).getByRole("link", { name: "Escenarios" });
    await u.click(enlace);
    expect(await titulo("Escenarios de sensibilidad")).toBeInTheDocument();
    expect(ruta()).toBe("/obra/empresa/7/control/escenarios");
    const despues = within(screen.getByRole("navigation", { name: "Opciones de Anticipar" })).getByRole("link", { name: "Escenarios" });
    expect(despues).toBe(enlace);
    expect(despues).toHaveFocus();
    expect(despues).toHaveAttribute("aria-current", "page");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  test("pasar de una subvista a otra de la misma obra no vuelve a fijarla ni a leer su ficha", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/control/reajuste" });
    await titulo("Reajuste de precios");
    await waitFor(() => expect(servidor.de("GET", "/v1/obras/resumen")).toHaveLength(1));
    await u.click(within(screen.getByRole("navigation", { name: "Opciones de Anticipar" })).getByRole("link", { name: "Escenarios" }));
    await titulo("Escenarios de sensibilidad");
    await new Promise((r) => setTimeout(r, 30));
    expect({ fijadas: servidor.de("PUT", "/v1/sesion/proyecto").length, fichas: servidor.de("GET", "/v1/obras/resumen").length }).toEqual({ fijadas: 1, fichas: 1 });
  });
});

// Foco 3 de la revisión: los enlaces de las barras están dentro del lienzo, que el marco no intercepta; por eso la barra
// pregunta ella misma (como useNavegarSeguro). Pasar entre Partidas y Componer no pregunta: ProveedorDeLaHoja.test.tsx.
describe("Marco: foco y título al navegar (A5)", () => {
  test("al cambiar de espacio con la barra lateral, el foco va al h1 de la pantalla nueva y la ventana la nombra", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    await u.click(within(screen.getByRole("complementary", { name: "Barra lateral" })).getByRole("link", { name: "Inicio" }));
    const h1 = await titulo("Vista general");
    await waitFor(() => expect(h1).toHaveFocus());
    expect(h1).toHaveAttribute("tabindex", "-1");
    expect(document.title.startsWith("Vista general")).toBe(true);
  });

  test("la frontera: dentro de la obra el foco se queda en el enlace del conmutador; al pasar a la Vista general va al h1", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/control/reajuste" });
    await titulo("Reajuste de precios");
    const enlace = within(screen.getByRole("navigation", { name: "Opciones de Anticipar" })).getByRole("link", { name: "Escenarios" });
    await u.click(enlace);
    await titulo("Escenarios de sensibilidad");
    await new Promise((r) => setTimeout(r, 80));
    expect(enlace).toHaveFocus();
    await u.click(within(screen.getByRole("complementary", { name: "Barra lateral" })).getByRole("link", { name: "Inicio" }));
    const h1 = await titulo("Vista general");
    await waitFor(() => expect(h1).toHaveFocus());
  });

  test("con replace no se fuerza el foco al h1", async () => {
    const u = userEvent.setup();
    function IrConReplace() {
      const navegar = useNavigate();
      return (
        <>
          <h1>Presupuesto</h1>
          <button type="button" onClick={() => navegar("/obra/empresa/7/mercado", { replace: true })}>
            Redirigir
          </button>
        </>
      );
    }
    montar({ en: "/obra/empresa/7/presupuesto", paginas: ligeras({ hoja: IrConReplace }) });
    await titulo("Presupuesto");
    await u.click(screen.getByRole("button", { name: "Redirigir" }));
    const h1 = await titulo("Estudio de mercado");
    await new Promise((r) => setTimeout(r, 80));
    expect(ruta()).toBe("/obra/empresa/7/mercado");
    expect(h1).not.toHaveFocus();
  });

  // Auditoría de B0, hallazgo 8: la secuencia que distingue «se actualizó el espacio previo» de «no». De la obra a la
  // Vista general cambia el espacio (el foco va al h1); de ahí a Pendientes no (el foco se queda en el enlace).
  test("de la obra a la Vista general el foco va al h1; a Pendientes, dentro de Inicio, se queda en el enlace", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    await u.click(within(screen.getByRole("complementary", { name: "Barra lateral" })).getByRole("link", { name: "Inicio" }));
    const general = await titulo("Vista general");
    await waitFor(() => expect(general).toHaveFocus());
    const enlace = within(screen.getByRole("navigation", { name: "Inicio" })).getByRole("link", { name: "Pendientes" });
    await u.click(enlace);
    await titulo("Pendientes");
    await new Promise((r) => setTimeout(r, 80));
    expect(ruta()).toBe("/inicio/pendientes");
    expect(enlace).toHaveFocus();
    // El enlace de Pendientes está en el contenido, donde el foco ya se respeta (hallazgo 9): el que prueba que el espacio previo
    // se actualizó es uno de fuera, el de la barra lateral. De Pendientes a la Vista general es el mismo espacio: se queda en él.
    const lateral = within(screen.getByRole("complementary", { name: "Barra lateral" })).getByRole("link", { name: "Inicio" });
    await u.click(lateral);
    await waitFor(() => expect(ruta()).toBe("/inicio/general"));
    await new Promise((r) => setTimeout(r, 80));
    expect(lateral).toHaveFocus();
  });

  // Una redirección de la carga inicial (`/hoja` sin obra acaba en `/inicio/pendientes`) también deja el espacio previo al día:
  // la primera navegación entre vistas de Inicio con un enlace de fuera del contenido no fuerza el foco.
  test("tras la redirección de la carga inicial, pasar a otra vista de Inicio desde la barra lateral deja el foco en su enlace", async () => {
    const u = userEvent.setup();
    montar({ en: "/hoja" });
    await titulo("Pendientes");
    expect(ruta()).toBe("/inicio/pendientes");
    const lateral = within(screen.getByRole("complementary", { name: "Barra lateral" })).getByRole("link", { name: "Inicio" });
    await u.click(lateral);
    await waitFor(() => expect(ruta()).toBe("/inicio/general"));
    await new Promise((r) => setTimeout(r, 80));
    expect(lateral).toHaveFocus();
  });

  // Hallazgo 6: la marca de la barra de arriba va a «/», que redirige (`replace`) a la Vista general. Es un cambio de espacio:
  // el foco va al h1 aunque la ruta termine tras una redirección.
  test("la marca «Sílice» de la barra de arriba, desde una obra, deja el foco en el h1 de la Vista general", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    const marca = within(screen.getByRole("banner")).getByRole("link", { name: "Sílice" });
    await u.click(marca);
    const general = await titulo("Vista general");
    await waitFor(() => expect(general).toHaveFocus());
    expect(ruta()).toBe("/inicio/general");
    expect(marca).not.toHaveFocus();
  });

  // Hallazgo 7: el título de la ventana tiene una sola fuente (la ubicación del marco). El h1 de la pantalla («Riesgo de la
  // obra») no empieza como la sección («Riesgo») y antes pisaba el título y perdía el nombre de la obra.
  test("al abrir una sección cuyo h1 no empieza como ella, el título de la ventana conserva la obra", async () => {
    const u = userEvent.setup();
    function Mesa() {
      const ir = useNavigate();
      return (
        <>
          <h1>Inicio de presupuestos y obras</h1>
          <button type="button" onClick={() => void ir("/obra/empresa/7/riesgo")}>
            Ir al riesgo
          </button>
        </>
      );
    }
    montar({ en: RUTA_DE_LA_MESA, paginas: conLaMesa(Mesa) });
    await u.click(await screen.findByRole("button", { name: "Ir al riesgo" }));
    const h1 = await titulo("Riesgo de la obra");
    await waitFor(() => expect(h1).toHaveFocus());
    expect(document.title).toBe("Riesgo · Casa Demo · Sílice");
  });

  // Si el marco no sabe nombrar la ruta (`ubicar` da null), el h1 es la única fuente y nombra la ventana.
  test("una pantalla que el marco no nombra da su h1 a la ventana", async () => {
    const u = userEvent.setup();
    function Mesa() {
      const ir = useNavigate();
      return (
        <>
          <h1>Inicio de presupuestos y obras</h1>
          <button type="button" onClick={() => void ir("/rara")}>
            Ir a la rara
          </button>
        </>
      );
    }
    const paginas = [...conLaMesa(Mesa), { ...conLaMesa(Mesa)[0]!, id: "rara", titulo: "" } satisfies PaginaDef];
    const rara = paginas.find((p) => p.id === "rara")!;
    rara.cargar = async () => ({ default: () => <h1>Pantalla rara</h1> });
    montar({ en: RUTA_DE_LA_MESA, paginas });
    await u.click(await screen.findByRole("button", { name: "Ir a la rara" }));
    const h1 = await titulo("Pantalla rara");
    await waitFor(() => expect(h1).toHaveFocus());
    expect(document.title).toBe("Pantalla rara · Sílice");
  });

  // Hallazgo 9: quien llegue primero gana. Una pantalla que enfoca su propio campo al montarse conserva el foco.
  test("una pantalla que enfoca su propio campo al montarse conserva el foco en él", async () => {
    const u = userEvent.setup();
    function Mesa() {
      const ir = useNavigate();
      return (
        <>
          <h1>Inicio de presupuestos y obras</h1>
          <button type="button" onClick={() => void ir("/precios/simulador")}>
            Ir al simulador
          </button>
        </>
      );
    }
    function ConCampo() {
      const campo = useRef<HTMLInputElement>(null);
      useEffect(() => campo.current?.focus(), []);
      return (
        <>
          <h1>Simulador de listas</h1>
          <input ref={campo} aria-label="Lista" />
        </>
      );
    }
    montar({ en: RUTA_DE_LA_MESA, paginas: conLaMesa(Mesa, { simulador: ConCampo }) });
    await u.click(await screen.findByRole("button", { name: "Ir al simulador" }));
    const h1 = await titulo("Simulador de listas");
    await new Promise((r) => setTimeout(r, 120));
    expect(screen.getByRole("textbox", { name: "Lista" })).toHaveFocus();
    expect(h1).not.toHaveFocus();
  });
});

describe("Marco: salir de una sección o subvista con cambios sin guardar (F6, T5)", () => {
  function HojaSucia() {
    useFormularioSucio("hoja", true);
    return <h1>Presupuesto</h1>;
  }
  function ComponerSucio() {
    useFormularioSucio("componer", true);
    return <h1>Componer una partida</h1>;
  }

  test("con la Hoja a medio llenar, pasar a otra sección desde la barra de la obra pregunta; «Quedarme» deja la ruta igual", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto", paginas: ligeras({ hoja: HojaSucia }) });
    await titulo("Presupuesto");
    const barra = screen.getByRole("navigation", { name: "Opciones de Presupuestar" });
    await u.click(within(barra).getByRole("link", { name: "Precios de mercado" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    expect(ruta()).toBe("/obra/empresa/7/presupuesto");
    await u.click(within(barra).getByRole("link", { name: "Precios de mercado" }));
    await u.click(within(await screen.findByRole("dialog", { name: "Cambios sin guardar" })).getByRole("button", { name: "Salir y descartar" }));
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/mercado"));
  });

  test("con Componer a medio llenar, volver a Presupuesto desde el conmutador pregunta", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto/componer", paginas: ligeras({ componer: ComponerSucio }) });
    await titulo("Componer una partida");
    await u.click(within(screen.getByRole("navigation", { name: "Opciones de Presupuestar" })).getByRole("link", { name: "Partidas" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    expect(ruta()).toBe("/obra/empresa/7/presupuesto/componer");
  });

  test("sin nada que perder, la barra navega sin preguntar", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    // Versiones no es una herramienta: se llega por el menú «Versión» de la barra de la obra.
    await u.click(within(screen.getByRole("region", { name: "Obra abierta" })).getByRole("button", { name: "Versión" }));
    await u.click(await screen.findByRole("menuitem", { name: "Versiones" }));
    expect(await titulo("Versiones")).toBeInTheDocument();
    expect(screen.queryByRole("dialog", { name: "Cambios sin guardar" })).toBeNull();
  });
});

// Contrato de rutas 2.4: las direcciones viejas de las pantallas que ahora son subvistas de la obra redirigen con replace,
// conservando la consulta, a la subvista de la obra de la sesión; sin obra, a Pendientes.
describe("Marco: las direcciones viejas de las subvistas de la obra (F6, T5)", () => {
  const TABLA_2_4_OBRA: readonly (readonly [string, string])[] = [
    ["/tablero", "resumen/tablero"],
    ["/componer", "presupuesto/componer"],
    ["/revisar", "aprobaciones/revisar"],
    ["/entregar", "aprobaciones/entregar"],
    ["/actualizacion", "mercado/actualizar"],
    ["/reajuste", "control/reajuste"],
    ["/escenarios", "control/escenarios"],
  ];

  test.each(TABLA_2_4_OBRA)("%s, con la obra 3 de «Carpeta Sur.db» en la sesión, acaba en /obra/Carpeta%20Sur.db/3/%s", async (de, a) => {
    instalar(enSur);
    montar({ sesion: sesionConObra("3"), en: de });
    await waitFor(() => expect(ruta()).toBe(`/obra/Carpeta%20Sur.db/3/${a}`));
  });

  test.each(TABLA_2_4_OBRA)("%s?codigo=OBRA-07&volver=hoja conserva la consulta al llegar a %s", async (de, a) => {
    instalar(enSur);
    montar({ sesion: sesionConObra("3"), en: `${de}?codigo=OBRA-07&volver=hoja` });
    await waitFor(() => expect(ruta()).toBe(`/obra/Carpeta%20Sur.db/3/${a}?codigo=OBRA-07&volver=hoja`));
  });

  test.each(TABLA_2_4_OBRA)("%s, sin obra en la sesión, acaba en #/inicio/pendientes", async (de) => {
    montar({ en: de });
    expect(await titulo("Pendientes")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/pendientes");
  });

  test("mientras llegan las obras de la sesión no redirige a Pendientes: espera", async () => {
    instalar(enSur);
    montar({ sesion: sesionConObra("3"), en: "/reajuste" });
    expect(screen.queryByRole("heading", { level: 1, name: "Pendientes" })).toBeNull();
    await waitFor(() => expect(ruta()).toBe("/obra/Carpeta%20Sur.db/3/control/reajuste"));
  });

  test("el buscador lleva a una subvista por su dirección corta, que redirige a la obra de la sesión", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    await u.keyboard("{Control>}k{/Control}");
    await u.type(screen.getByRole("combobox", { name: "Buscar una obra, sección o pantalla" }), "reajuste");
    await u.keyboard("{Enter}");
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/control/reajuste"));
  });
});

// Decisión de Eugenio (2026-11-04): al elegir una obra en la barra lateral se abre su Resumen; no se conserva la sección.
describe("Marco: elegir una obra en la barra lateral abre su Presupuesto (F6, T5 y D1 de B1)", () => {
  test("desde una subvista de una obra, elegir otra abre el Presupuesto de la otra", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/control/reajuste" });
    await titulo("Reajuste de precios");
    const lista = await screen.findByRole("list", { name: "Obras" });
    expect(within(lista).getByRole("link", { name: "Casa Demo" })).toHaveAttribute("aria-current", "page");
    expect(within(lista).getByRole("link", { name: "Torre B" })).not.toHaveAttribute("aria-current");
    await u.click(within(lista).getByRole("link", { name: "Torre B" }));
    expect(await titulo("Presupuesto")).toBeInTheDocument();
    expect(ruta()).toBe("/obra/empresa/8/presupuesto");
    expect(within(screen.getByRole("list", { name: "Obras" })).getByRole("link", { name: "Torre B" })).toHaveAttribute("aria-current", "page");
  });

  test("elegir la obra que ya está abierta, desde otra sección, lleva a su Presupuesto", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/versiones" });
    await titulo("Versiones");
    await u.click(within(await screen.findByRole("list", { name: "Obras" })).getByRole("link", { name: "Casa Demo" }));
    expect(await titulo("Presupuesto")).toBeInTheDocument();
    expect(ruta()).toBe("/obra/empresa/7/presupuesto");
  });
});

describe("Marco: cambiar de obra con cambios sin guardar (foco 5)", () => {
  function HojaSucia() {
    useFormularioSucio("hoja", true);
    return <h1>Presupuesto</h1>;
  }

  test("con la Hoja a medio llenar, elegir otra obra en la barra lateral pregunta; «Quedarme» deja la ruta igual", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto", paginas: ligeras({ hoja: HojaSucia }) });
    expect(await titulo("Presupuesto")).toBeInTheDocument();
    const lista = await screen.findByRole("list", { name: "Obras" });
    await u.click(await within(lista).findByRole("link", { name: "Torre B" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    expect(pregunta).toHaveAccessibleDescription("Tiene cambios sin guardar en Presupuesto. Si sale de esta pantalla, se perderán.");
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    expect(screen.queryByRole("dialog", { name: "Cambios sin guardar" })).toBeNull();
    expect(ruta()).toBe("/obra/empresa/7/presupuesto");
    await u.click(within(lista).getByRole("link", { name: "Torre B" }));
    await u.click(within(await screen.findByRole("dialog", { name: "Cambios sin guardar" })).getByRole("button", { name: "Salir y descartar" }));
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/8/presupuesto"));
  });

  test("con un borrador de la Hoja con cambios, ir a una obra de otra carpeta pregunta por él y «Quedarme» no cambia de carpeta", async () => {
    const u = userEvent.setup();
    instalar((estado) => {
      estado.borradores = [{ id: "b-1", proyecto: "7", version: "001", cambios: 2, rev: 3, tocado: "2026-10-27T10:00:00" }];
    });
    montar({ en: "/obra/empresa/7/presupuesto" });
    expect(await titulo("Presupuesto")).toBeInTheDocument();
    await u.click(await within(await screen.findByRole("list", { name: "Obras" })).findByRole("link", { name: "Galpón Sur" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    expect(pregunta).toHaveAccessibleDescription("Tiene cambios sin guardar en Hoja de Casa Demo. Si cambia de carpeta, se perderán.");
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    await new Promise((r) => setTimeout(r, 30));
    expect(servidor.de("POST", "/v1/casos/actual")).toEqual([]);
    expect(ruta()).toBe("/obra/empresa/7/presupuesto");
  });

  // Hallazgo MAYOR 1 del árbitro final: los enlaces de la Vista general están dentro de #contenido, que el marco no
  // interceptaba, y abrir una obra de otra carpeta olvida en el servidor los borradores de la Hoja.
  function VistaConEnlaces() {
    return (
      <>
        <h1>Vista general</h1>
        <Link to="/obra/Carpeta%20Sur.db/3/resumen">Galpón Sur desde la vista</Link>
        <Link to="/obra/empresa/8/resumen">Torre B desde la vista</Link>
      </>
    );
  }
  const conBorrador = (estado: EstadoDelServidor) => {
    estado.borradores = [{ id: "b-1", proyecto: "7", version: "001", cambios: 2, rev: 3, tocado: "2026-10-27T10:00:00" }];
  };

  test("un enlace del contenido (Vista general) a una obra de otra carpeta, con un borrador con cambios, pregunta; «Quedarme» no cambia de carpeta", async () => {
    const u = userEvent.setup();
    instalar(conBorrador);
    montar({ en: "/inicio/general", paginas: ligeras({ inicio: VistaConEnlaces }) });
    expect(await titulo("Vista general")).toBeInTheDocument();
    await u.click(await screen.findByRole("link", { name: "Galpón Sur desde la vista" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    expect(pregunta).toHaveAccessibleDescription("Tiene cambios sin guardar en Hoja de Casa Demo. Si cambia de carpeta, se perderán.");
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    await new Promise((r) => setTimeout(r, 30));
    expect(servidor.de("POST", "/v1/casos/actual")).toEqual([]);
    expect(ruta()).toBe("/inicio/general");
  });

  test("confirmar la pregunta del enlace del contenido sí cambia de carpeta", async () => {
    const u = userEvent.setup();
    instalar(conBorrador);
    montar({ en: "/inicio/general", paginas: ligeras({ inicio: VistaConEnlaces }) });
    await u.click(await screen.findByRole("link", { name: "Galpón Sur desde la vista" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    await u.click(within(pregunta).getByRole("button", { name: "Cambiar y descartar" }));
    await waitFor(() => expect(ruta()).toBe("/obra/Carpeta%20Sur.db/3/resumen"));
    await waitFor(() => expect(servidor.de("POST", "/v1/casos/actual").map((l) => l.cuerpo)).toEqual([{ nombre: SUR }]));
  });

  test("un enlace del contenido a otra carpeta, sin nada que perder, se abre sin preguntar", async () => {
    const u = userEvent.setup();
    montar({ en: "/inicio/general", paginas: ligeras({ inicio: VistaConEnlaces }) });
    await u.click(await screen.findByRole("link", { name: "Galpón Sur desde la vista" }));
    await waitFor(() => expect(ruta()).toBe("/obra/Carpeta%20Sur.db/3/resumen"));
    expect(screen.queryByRole("dialog", { name: "Cambios sin guardar" })).toBeNull();
  });

  test("un enlace del contenido a una obra de la misma carpeta, con un borrador, no pregunta (el borrador se conserva)", async () => {
    const u = userEvent.setup();
    instalar(conBorrador);
    montar({ en: "/inicio/general", paginas: ligeras({ inicio: VistaConEnlaces }) });
    await u.click(await screen.findByRole("link", { name: "Torre B desde la vista" }));
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/8/resumen"));
    expect(screen.queryByRole("dialog", { name: "Cambios sin guardar" })).toBeNull();
    expect(servidor.de("POST", "/v1/casos/actual")).toEqual([]);
  });

  test("con un formulario sucio y un enlace del contenido a otra carpeta, la pregunta es una sola", async () => {
    const u = userEvent.setup();
    function VistaSucia() {
      useFormularioSucio("inicio", true);
      return <VistaConEnlaces />;
    }
    montar({ en: "/inicio/general", paginas: ligeras({ inicio: VistaSucia }) });
    await u.click(await screen.findByRole("link", { name: "Galpón Sur desde la vista" }));
    expect(await screen.findAllByRole("dialog", { name: "Cambios sin guardar" })).toHaveLength(1);
    await u.click(within(screen.getByRole("dialog", { name: "Cambios sin guardar" })).getByRole("button", { name: "Quedarme" }));
    expect(screen.queryByRole("dialog", { name: "Cambios sin guardar" })).toBeNull();
    expect(servidor.de("POST", "/v1/casos/actual")).toEqual([]);
  });

  test("sin nada que perder, una obra de otra carpeta se abre sin preguntar", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto" });
    expect(await titulo("Presupuesto")).toBeInTheDocument();
    await u.click(await within(await screen.findByRole("list", { name: "Obras" })).findByRole("link", { name: "Galpón Sur" }));
    await waitFor(() => expect(ruta()).toBe("/obra/Carpeta%20Sur.db/3/presupuesto"));
    expect(screen.queryByRole("dialog", { name: "Cambios sin guardar" })).toBeNull();
    await waitFor(() => expect(servidor.de("POST", "/v1/casos/actual").map((l) => l.cuerpo)).toEqual([{ nombre: SUR }]));
  });
});

describe("Marco: lo que se monta con él", () => {
  test("Ctrl+K y el botón abren el buscador; Esc lo cierra y el foco vuelve al botón", async () => {
    const u = userEvent.setup();
    montar();
    await titulo("Pendientes");
    const boton = within(screen.getByRole("banner")).getByRole("button", { name: "Buscar una obra, sección o pantalla… (Ctrl+K)" });
    await u.click(boton);
    expect(screen.getByRole("dialog", { name: "Buscar" })).toBeInTheDocument();
    await u.keyboard("{Escape}");
    expect(screen.queryByRole("dialog", { name: "Buscar" })).toBeNull();
    expect(boton).toHaveFocus();
    document.getElementById("contenido")?.focus();
    await u.keyboard("{Control>}k{/Control}");
    expect(screen.getByRole("dialog", { name: "Buscar" })).toBeInTheDocument();
  });

  test("elegir en el buscador una obra con cambios sin guardar también pregunta", async () => {
    const u = userEvent.setup();
    function ComponerSucio() {
      useFormularioSucio("componer", true);
      return <h1>Componer una partida</h1>;
    }
    montar({ en: "/obra/empresa/7/presupuesto/componer", paginas: ligeras({ componer: ComponerSucio }) });
    await titulo("Componer una partida");
    await u.keyboard("{Control>}k{/Control}");
    await u.type(screen.getByRole("combobox", { name: "Buscar una obra, sección o pantalla" }), "torre");
    await u.keyboard("{Enter}");
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    expect(ruta()).toBe("/obra/empresa/7/presupuesto/componer");
  });

  test("«Cambios sin guardar» está montado: una pregunta de una página se contesta", async () => {
    const u = userEvent.setup();
    function Pregunta() {
      const [respuesta, setRespuesta] = useState("sin contestar");
      return (
        <>
          <h1>Componer una partida</h1>
          <button type="button" onClick={() => void confirmarSalida("salir", ["la partida nueva"]).then((s) => setRespuesta(String(s)))}>
            Preguntar
          </button>
          <p>{`respuesta: ${respuesta}`}</p>
        </>
      );
    }
    montar({ en: "/obra/empresa/7/presupuesto/componer", paginas: ligeras({ componer: Pregunta }) });
    await u.click(await screen.findByRole("button", { name: "Preguntar" }));
    await u.click(within(await screen.findByRole("dialog", { name: "Cambios sin guardar" })).getByRole("button", { name: "Quedarme" }));
    expect(await screen.findByText("respuesta: false")).toBeInTheDocument();
  });

  test("«Nueva obra» pedida desde la mesa abre el diálogo de la barra lateral, que dice dónde se creará", async () => {
    const u = userEvent.setup();
    function MesaConNuevaObra() {
      const { abrirNuevaObra } = useAplicacion();
      return (
        <>
          <h1>Inicio de presupuestos y obras</h1>
          <button type="button" onClick={() => abrirNuevaObra?.()}>
            Cree su primera obra
          </button>
        </>
      );
    }
    montar({ en: RUTA_DE_LA_MESA, paginas: conLaMesa(MesaConNuevaObra) });
    await u.click(await screen.findByRole("button", { name: "Cree su primera obra" }));
    const dialogo = await screen.findByRole("dialog", { name: "Nueva obra" });
    expect(await within(dialogo).findByText("Se creará en Carpeta de la empresa")).toBeInTheDocument();
    expect(screen.getAllByRole("dialog", { name: "Nueva obra" })).toHaveLength(1);
  });

  // Pasada en el navegador del cierre de F2: la barra lateral es fija al desplazar (`position: sticky`) y por eso apila
  // aparte; «Nueva obra», dibujado dentro de ella, quedaba debajo del contenido. Los diálogos se pintan en el cuerpo del
  // documento, fuera de la barra lateral y del marco.
  test("el diálogo «Nueva obra» se pinta fuera de la barra lateral, encima de todo", async () => {
    const u = userEvent.setup();
    montar();
    await titulo("Pendientes");
    const lateral = screen.getByRole("complementary", { name: "Barra lateral" });
    await u.click(within(lateral).getByRole("button", { name: "Nueva obra" }));
    const dialogo = await screen.findByRole("dialog", { name: "Nueva obra" });
    expect(lateral).not.toContainElement(dialogo);
    expect(dialogo.closest(".silice-marco")).toBeNull();
  });

  test("en la carpeta de demostración la barra lo dice", async () => {
    instalar((estado) => {
      estado.casos = [...estado.casos, caso("demostracion.db")];
      estado.actual = caso("demostracion.db");
    });
    montar();
    expect(
      await within(screen.getByRole("banner")).findByRole("button", { name: "Demostración: está viendo datos inventados" }),
    ).toBeInTheDocument();
  });

  // F1: desde una obra de demostracion.db, «Volver a la carpeta de la empresa» debe salir de /obra/demostracion.db/...
  // hacia Inicio y conservar el aviso de cambio de carpeta sin que useObraDeLaRuta reabra demostracion.db.
  test("F1: desde una obra de demostracion.db, «Volver a la carpeta de la empresa» lleva a Inicio con el aviso y no la reabre", async () => {
    const u = userEvent.setup();
    instalar((estado) => {
      estado.casos = [...estado.casos, caso("demostracion.db")];
      estado.actual = caso("demostracion.db");
    });
    const base = servidor.fetchFalso;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (entrada: RequestInfo | URL, init?: RequestInit) => {
        if (String(entrada) === "/v1/obras/todas" && (init?.method ?? "GET") === "GET") {
          const baseTodas = obrasTodas(servidor.estado);
          return json({
            ...baseTodas,
            obras: [
              ...baseTodas.obras,
              {
                carpeta: "demostracion.db",
                carpeta_titulo: "demostracion",
                obra_id: 10,
                obra: "Obra Demo",
                version_codigo: "001",
              },
            ],
          });
        }
        return base(entrada, init);
      }),
    );

    montar({ en: "/obra/demostracion.db/10/presupuesto" });
    expect(await titulo("Presupuesto")).toBeInTheDocument();
    const barra = screen.getByRole("banner");
    await u.click(await within(barra).findByRole("button", { name: "Demostración: está viendo datos inventados" }));
    await u.click(within(barra).getByRole("button", { name: "Volver a la carpeta de la empresa" }));

    expect(await titulo("Vista general")).toBeInTheDocument();
    expect(ruta()).toBe("/inicio/general");
    expect(await screen.findByText("Carpeta cambiada")).toBeInTheDocument();
    expect(screen.getByText("Ahora trabaja con la carpeta «silice».")).toBeInTheDocument();
    expect(servidor.de("DELETE", "/v1/casos/actual")).toHaveLength(1);
    expect(servidor.de("POST", "/v1/casos/actual")).toEqual([]);
    expect(await within(barra).findByText("Inicio / Vista general")).toBeInTheDocument();
  });

  test("con un recorrido en curso su columna acompaña al contenido", async () => {
    iniciarRecorrido(RECORRIDO_AUDITAR);
    montar({ en: "/auditoria/libros" });
    await titulo("Libro de la empresa");
    expect(screen.getByRole("complementary", { name: "Recorrido" })).toBeInTheDocument();
  });

  test("«Salir de la sesión», en la cabecera de la Cuenta, cierra el recorrido en curso y llama a alSalir", async () => {
    const u = userEvent.setup();
    iniciarRecorrido(RECORRIDO_AUDITAR);
    const { alSalir } = montar();
    await titulo("Pendientes");
    await u.click(screen.getByRole("link", { name: "Cuenta de Ana Pérez" }));
    await u.click(await screen.findByRole("button", { name: "Salir de la sesión" }));
    expect(alSalir).toHaveBeenCalledTimes(1);
    expect(recorridoEnCurso()).toBeNull();
  });

  test("un 401 de la API da la sesión por vencida", async () => {
    servidor = servidorFalso(estadoInicial(), (_metodo, r) => (r === "/v1/casos" ? json({ detalle: "Sin sesión." }, 401) : undefined));
    vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
    const { alExpirar } = montar();
    await waitFor(() => expect(alExpirar).toHaveBeenCalled());
  });

  test("«Saltar al contenido» es lo primero que se alcanza con Tab y hay una sola región main", async () => {
    const u = userEvent.setup();
    montar();
    await titulo("Pendientes");
    expect(screen.getAllByRole("main")).toHaveLength(1);
    await u.tab();
    expect(screen.getByRole("button", { name: "Saltar al contenido" })).toHaveFocus();
    await u.keyboard("{Enter}");
    expect(screen.getByRole("main")).toHaveFocus();
  });

  test("si la pantalla no carga lo dice, sin «página»", async () => {
    const rota: PaginaDef[] = ligeras().map((p) => (p.id === "simulador" ? { ...p, cargar: () => Promise.reject(new Error("sin red")) } : p));
    montar({ en: "/precios/simulador", paginas: rota });
    expect(await screen.findByText("No se pudo abrir la pantalla")).toBeInTheDocument();
    expect(screen.getByRole("main")).not.toHaveTextContent(/página/i);
  });

  test("abrir otra carpeta desde una pantalla (la Cuenta) avisa con su nombre, sin «carpeta de trabajo»", async () => {
    const u = userEvent.setup();
    function AbrirS2() {
      const { abrirCarpeta } = useAplicacion();
      return (
        <>
          <p>Administración</p>
          <button type="button" onClick={() => void abrirCarpeta?.("s2.db")}>
            Abrir s2
          </button>
        </>
      );
    }
    const admin = sesionDe("ana", { acciones: [...ACCIONES.ana, "administrar_cuentas"] });
    montar({ sesion: admin, en: "/cuenta/cuentas", paginas: ligeras({ administracion: AbrirS2 }) });
    await u.click(await screen.findByRole("button", { name: "Abrir s2" }));
    expect(await screen.findByText("Ahora trabaja con la carpeta «s2».")).toBeInTheDocument();
    expect(servidor.de("POST", "/v1/casos/actual").map((l) => l.cuerpo)).toEqual([{ nombre: "s2.db" }]);
  });

  // Prueba en vivo del 2026-11-18: la barra lateral tenía su propia lectura de las obras; al abrir otra carpeta el marco
  // recargaba la suya y la barra seguía con la carpeta anterior («Se creará en…» decía la de antes).
  // Prueba en vivo (2026-11-18): tras abrir otra carpeta la barra seguía con los contadores de pendientes de la anterior
  // hasta recargar o entrar en Inicio.
  test("al abrir otra carpeta los contadores de pendientes de la barra son los de la nueva, pedidos una vez", async () => {
    const u = userEvent.setup();
    const pendiente = (n: number) => ({
      carpeta: null,
      obra_id: n,
      obra: `Obra ${n}`,
      grupo: "compras",
      urgencia: "aviso",
      texto: `Falta algo ${n}`,
      accion: { texto: "Abrir el presupuesto", pagina: "hoja" },
    });
    let pedidos = 0;
    const base = servidor.fetchFalso;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (entrada: RequestInfo | URL, init?: RequestInit) => {
        if (String(entrada) === "/v1/obras/pendientes/todas") {
          pedidos += 1;
          const n = servidor.estado.actual.nombre === SUR ? 2 : 1;
          return json({ pendientes: Array.from({ length: n }, (_, i) => pendiente(i + 1)), carpetas_omitidas: 0 });
        }
        return base(entrada, init);
      }),
    );
    function AbrirSur() {
      const { abrirCarpeta } = useAplicacion();
      return (
        <button type="button" onClick={() => void abrirCarpeta?.(SUR)}>
          Abrir Sur
        </button>
      );
    }
    const admin = sesionDe("ana", { acciones: [...ACCIONES.ana, "administrar_cuentas"] });
    montar({ sesion: admin, en: "/cuenta/cuentas", paginas: ligeras({ administracion: AbrirSur }) });
    const lateral = await screen.findByRole("complementary", { name: "Barra lateral" });
    expect(await within(lateral).findByRole("link", { name: "Inicio, 1 por hacer" })).toBeInTheDocument();
    expect(pedidos).toBe(1);
    await u.click(await screen.findByRole("button", { name: "Abrir Sur" }));
    expect(await within(lateral).findByRole("link", { name: "Inicio, 2 por hacer" })).toBeInTheDocument();
    expect(pedidos).toBe(2);
  });

  test("al abrir otra carpeta, «Nueva obra» dice la nueva y la lista de obras se pide una sola vez por carga", async () => {
    const u = userEvent.setup();
    function AbrirSur() {
      const { abrirCarpeta } = useAplicacion();
      return (
        <button type="button" onClick={() => void abrirCarpeta?.(SUR)}>
          Abrir Sur
        </button>
      );
    }
    const admin = sesionDe("ana", { acciones: [...ACCIONES.ana, "administrar_cuentas"] });
    montar({ sesion: admin, en: "/cuenta/cuentas", paginas: ligeras({ administracion: AbrirSur }) });
    const lateral = await screen.findByRole("complementary", { name: "Barra lateral" });
    await waitFor(() => expect(servidor.de("GET", "/v1/obras/todas")).toHaveLength(1));
    await u.click(await screen.findByRole("button", { name: "Abrir Sur" }));
    expect(await screen.findByText("Ahora trabaja con la carpeta «Carpeta Sur».")).toBeInTheDocument();
    await waitFor(() => expect(servidor.de("GET", "/v1/obras/todas")).toHaveLength(2));
    await u.click(within(lateral).getByRole("button", { name: "Nueva obra" }));
    const dialogo = await screen.findByRole("dialog", { name: "Nueva obra" });
    expect(await within(dialogo).findByText("Se creará en Carpeta Sur")).toBeInTheDocument();
    expect(servidor.de("GET", "/v1/obras/todas")).toHaveLength(2);
  });
});

// Arbitraje (2026-11-18): `recargadaPara` recordaba la última obra que pidió recargar la lista y no se reiniciaba al cambiar de
// carpeta: entrar en una obra de Sur, volver a la empresa y volver a entrar en la misma obra de Sur se saltaba la recarga y
// el contexto se quedaba con la carpeta vieja («Se creará en» decía la de la empresa).
describe("Marco: volver a entrar en la misma obra de otra carpeta tras pasar por la empresa", () => {
  test("la lista de obras se pone al día y «Nueva obra» dice la carpeta de Sur", async () => {
    const u = userEvent.setup();
    function Mandos() {
      const navegar = useNavigate();
      const { abrirCarpeta } = useAplicacion();
      return (
        <>
          <button type="button" onClick={() => navegar("/obra/Carpeta%20Sur.db/3/resumen")}>
            Ir a la obra de Sur
          </button>
          <button type="button" onClick={() => void abrirCarpeta?.("silice.db")}>
            Abrir la empresa
          </button>
          <button type="button" onClick={() => navegar("/cuenta/cuentas")}>
            Ir a la Cuenta
          </button>
        </>
      );
    }
    const admin = sesionDe("ana", { acciones: [...ACCIONES.ana, "administrar_cuentas"] });
    montar({ sesion: admin, en: "/cuenta/cuentas", paginas: ligeras({ administracion: Mandos, obras: Mandos }) });
    await u.click(await screen.findByRole("button", { name: "Ir a la obra de Sur" }));
    await waitFor(() => expect(servidor.de("PUT", "/v1/sesion/proyecto")).toHaveLength(1));
    await u.click(await screen.findByRole("button", { name: "Abrir la empresa" }));
    expect(await screen.findByText("Ahora trabaja con la carpeta «silice».")).toBeInTheDocument();
    await u.click(await screen.findByRole("button", { name: "Ir a la obra de Sur" }));
    await waitFor(() => expect(servidor.de("PUT", "/v1/sesion/proyecto")).toHaveLength(2));
    await u.click(await screen.findByRole("button", { name: "Ir a la Cuenta" }));
    const lateral = await screen.findByRole("complementary", { name: "Barra lateral" });
    await waitFor(() => expect(servidor.estado.actual.nombre).toBe(SUR));
    await u.click(within(lateral).getByRole("button", { name: "Nueva obra" }));
    const dialogo = await screen.findByRole("dialog", { name: "Nueva obra" });
    expect(await within(dialogo).findByText("Se creará en Carpeta Sur")).toBeInTheDocument();
  });
});

describe("Marco: cuentas sin obras que leer", () => {
  // Pasada en el navegador del cierre de F2: el administrador (sin `leer_proyecto`) veía «No se pudieron cargar las
  // obras» porque el marco pedía `GET /v1/obras/todas` y la API contestaba 403. Sin el permiso no se pide (VB-9) y la
  // zona de obras no se pinta: lo que la cuenta no puede usar no aparece.
  test("sin leer_proyecto no pide las obras ni muestra la zona de obras con un error", async () => {
    const admin = sesionDe("admin");
    montar({ sesion: admin, en: "/cuenta/ayuda" });
    await titulo("Ayuda y acerca de Sílice");
    const lateral = screen.getByRole("complementary", { name: "Barra lateral" });
    expect(within(lateral).getByRole("link", { name: "Inicio" })).toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 30));
    expect(servidor.de("GET", "/v1/obras/todas")).toEqual([]);
    expect(within(lateral).queryByText("No se pudieron cargar las obras")).toBeNull();
    expect(within(lateral).queryByRole("heading", { name: "Obras" })).toBeNull();
  });
});

describe("Marco: vocabulario y alcance", () => {
  test("ningún texto visible del marco dice «módulo», «área», «página», «carpeta de trabajo» ni «Streamlit»", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    await u.keyboard("{Control>}k{/Control}");
    // La página montada es ligera (solo su h1): todo lo demás es del marco.
    for (const palabra of [/módulo/i, /área/i, /página/i, /carpeta de trabajo/i, /streamlit/i]) {
      expect(document.body.textContent).not.toMatch(palabra);
    }
  });

  // Toda pantalla que la cuenta puede usar se alcanza desde el marco: por Pendientes, por el árbol (secciones de la obra
  // y Empresa) o por el buscador. Acciones por rol de `datosDePrueba` (las de seguridad/permisos.py, escritas a mano).
  test.each(Object.keys(ACCIONES) as (keyof typeof ACCIONES)[])("ninguna pantalla usable queda inalcanzable para %s", (rol) => {
    const acciones = ACCIONES[rol];
    const oferta = ofertaDe(acciones, false);
    const alcanzables = new Set<string | null>([
      "obras",
      "inicio", // F6, T8: la Vista general es la entrada de la app (ruta índice)
      ...oferta.secciones.map((s) => s.pagina),
      ...oferta.cuenta.map((c) => c.pagina),
      ...oferta.herramientas.map((p) => p.id),
    ]);
    const usables = PAGINAS.filter((p) => usable(p, acciones, false)).map((p) => p.id);
    expect(usables.filter((id) => !alcanzables.has(id))).toEqual([]);
  });

  test("solo quien opera la arenera ve «Inicio de producción» en el buscador", () => {
    const deLaPagina = (acciones: readonly string[]) => ofertaDe(acciones, false).herramientas.map((p) => p.id);
    expect(deLaPagina(ACCIONES.rita)).not.toContain("produccion");
    expect(deLaPagina(ACCIONES.ana)).toContain("produccion");
  });
});

// Ronda 2 del árbitro (Tarea 8): el bloque «el foco no se pierde cuando la acción quita el control» de las pruebas del
// armazón anterior, llevado al marco. Al cambiar de pantalla, si el foco se perdió (lo tenía un control que ya no está),
// pasa al único h1 de la nueva; si lo tiene un control que sigue en el mismo espacio (un enlace de la barra de la obra) no se
// toca, pero al cambiar de espacio (barra lateral, barra de arriba, A5) el foco va al h1 aunque lo tenga el enlace; la carga inicial y sus redirecciones (`replace`) no lo roban; y el h1 de un esqueleto no lo retiene.
describe("Marco: el foco no se pierde cuando la acción quita el control", () => {
  function MesaQueVa() {
    const ir = useNavigate();
    return (
      <>
        <h1>Inicio de presupuestos y obras</h1>
        <button type="button" onClick={() => void ir("/precios/simulador")}>
          Ir al simulador
        </button>
        <button type="button" onClick={() => void ir("/obra/empresa/7/presupuesto")}>
          Ir a la obra
        </button>
      </>
    );
  }

  test.each([
    ["Ir al simulador", "Simulador de listas"],
    ["Ir a la obra", "Presupuesto"],
  ])("«%s», un botón de la pantalla que navega, deja el foco en el único h1 de la nueva («%s»)", async (boton, h1) => {
    const u = userEvent.setup();
    montar({ en: RUTA_DE_LA_MESA, paginas: conLaMesa(MesaQueVa) });
    await u.click(await screen.findByRole("button", { name: boton }));
    const nuevo = await titulo(h1);
    await waitFor(() => expect(nuevo).toHaveFocus(), { timeout: 3000 });
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(nuevo).toHaveAttribute("tabindex", "-1");
  });

  test("un enlace de la barra lateral deja el foco en el h1 de la pantalla nueva aunque lo tuviera él (A5)", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/resumen" });
    await titulo("Resumen de la obra");
    const enlace = within(screen.getByRole("complementary", { name: "Barra lateral" })).getByRole("link", { name: "Inicio" });
    await u.click(enlace);
    const nuevo = await titulo("Vista general");
    await waitFor(() => expect(nuevo).toHaveFocus());
    expect(enlace).not.toHaveFocus();
  });

  test("un enlace de la barra de la obra que sigue tras navegar conserva el foco", async () => {
    const u = userEvent.setup();
    // Entre secciones sin Hoja: pasar de o a una con Hoja monta otra vez la cabecera y la barra (otro árbol), y el foco pasa al h1.
    montar({ en: "/obra/empresa/7/mercado" });
    await titulo("Estudio de mercado");
    const enlace = await within(screen.getByRole("navigation", { name: "Herramientas de la obra" })).findByRole("link", { name: "Anticipar" });
    await u.click(enlace);
    await titulo("Control de obra");
    expect(ruta()).toBe("/obra/empresa/7/control");
    await new Promise((r) => setTimeout(r, 80));
    expect(enlace).toHaveFocus();
  });

  test("el enlace de la persona, en la barra de arriba, deja el foco en el h1 de la Cuenta (A5)", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    const enlace = within(screen.getByRole("banner")).getByRole("link", { name: "Cuenta de Ana Pérez" });
    await u.click(enlace);
    const nuevo = await titulo("Configuración");
    expect(ruta()).toBe("/cuenta/preferencias");
    await waitFor(() => expect(nuevo).toHaveFocus());
    expect(enlace).not.toHaveFocus();
    expect(enlace).toHaveAttribute("aria-current", "page");
  });

  test("un enlace que desaparece al navegar (el de un aviso) deja el foco en el h1 de la nueva", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/99/resumen" });
    await titulo("Esa obra ya no existe");
    await u.click(screen.getByRole("link", { name: "Volver a Pendientes" }));
    const nuevo = await titulo("Pendientes");
    expect(ruta()).toBe("/inicio/pendientes");
    expect(screen.queryByRole("link", { name: "Volver a Pendientes" })).toBeNull();
    await waitFor(() => expect(nuevo).toHaveFocus());
  });

  // `PUT /v1/sesion/proyecto` contesta 500 mientras `caida.caido`: la obra no se puede abrir («error»). `intentos`
  // cuenta los PUT que llegaron, para saber que «Reintentar» volvió a entrar.
  function conLaObraCaida() {
    const caida = { caido: true, intentos: 0 };
    const base = servidor.fetchFalso;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (entrada: RequestInfo | URL, init?: RequestInit) => {
        if (String(entrada) === "/v1/sesion/proyecto" && init?.method === "PUT") {
          caida.intentos += 1;
          if (caida.caido) return json({ detalle: "Falla interna." }, 500);
        }
        return base(entrada, init);
      }),
    );
    return caida;
  }
  const TEXTO_DE_LA_CAIDA = "Revise la conexión con Sílice y vuelva a intentarlo.";

  // Ronda 2 del árbitro: el estado «error» de la obra (servidor caído, 500) era el único sin h1, y el foco quedaba en
  // <body>. Ahora es un aviso con su h1, como «Esa obra ya no existe» y «Esta obra se abrió en otra pestaña».
  test("si la obra no se pudo abrir, el aviso tiene su h1 y el foco va a él; «Reintentar» la abre", async () => {
    const u = userEvent.setup();
    const caida = conLaObraCaida();
    montar({ en: RUTA_DE_LA_MESA, paginas: conLaMesa(MesaQueVa) });
    await u.click(await screen.findByRole("button", { name: "Ir a la obra" }));
    const aviso = await titulo("No se pudo abrir la obra");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByText(TEXTO_DE_LA_CAIDA)).toBeInTheDocument();
    await waitFor(() => expect(aviso).toHaveFocus());
    caida.caido = false;
    await u.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await titulo("Presupuesto")).toBeInTheDocument();
  });

  // Ronda 3 del árbitro: con el h1 el aviso solo se anunciaba si el foco iba a él, y no va en la carga inicial (un
  // enlace viejo o un marcador a la obra), tras un «Reintentar» que vuelve a fallar ni si el fallo tarda. El texto va en
  // una región que se anuncia sola (role="alert").
  test("entrar directo en una obra que no se puede abrir anuncia el aviso (role alert) sin mover el foco", async () => {
    conLaObraCaida();
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("No se pudo abrir la obra");
    expect(screen.getByRole("alert")).toHaveTextContent(TEXTO_DE_LA_CAIDA);
    expect(document.body).toHaveFocus();
  });

  test("«Reintentar» que vuelve a fallar deja la alerta y el foco en el h1 del aviso, no en <body>", async () => {
    const u = userEvent.setup();
    const caida = conLaObraCaida();
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("No se pudo abrir la obra");
    const antes = caida.intentos;
    await u.click(screen.getByRole("button", { name: "Reintentar" }));
    await waitFor(() => expect(caida.intentos).toBe(antes + 1));
    await waitFor(() => expect(screen.getByRole("heading", { level: 1, name: "No se pudo abrir la obra" })).toHaveFocus());
    expect(screen.getByRole("alert")).toHaveTextContent(TEXTO_DE_LA_CAIDA);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  test("«Reintentar» que acierta deja el foco en el h1 de la sección abierta", async () => {
    const u = userEvent.setup();
    const caida = conLaObraCaida();
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("No se pudo abrir la obra");
    caida.caido = false;
    await u.click(screen.getByRole("button", { name: "Reintentar" }));
    const seccion = await titulo("Presupuesto");
    await waitFor(() => expect(seccion).toHaveFocus());
    expect(screen.queryByRole("alert")).toBeNull();
  });

  // Ronda extra del árbitro: «Esta obra se abrió en otra pestaña» aparece de golpe por un mensaje de otra pestaña (quizá
  // mientras la persona escribe en la Hoja): se anuncia solo, y «Retomar», que quita su botón sin cambiar de ruta, deja
  // el foco en el h1 de la sección, como «Reintentar».
  const TEXTO_DE_OTRA_PESTANA = "Otra pestaña de Sílice abrió otra obra. Retómela aquí para seguir trabajando en esta.";
  async function abrirEnOtraPestana() {
    const canal: CanalDeObra = { onmessage: null, postMessage: vi.fn() };
    montar({ en: "/obra/empresa/7/presupuesto", canal });
    await titulo("Presupuesto");
    canal.onmessage?.({ data: { carpeta: SUR, obraId: 3 } } as MessageEvent);
    return titulo("Esta obra se abrió en otra pestaña");
  }

  test("el aviso «Esta obra se abrió en otra pestaña» se anuncia (role alert)", async () => {
    await abrirEnOtraPestana();
    expect(screen.getByRole("alert")).toHaveTextContent(TEXTO_DE_OTRA_PESTANA);
  });

  test("«Retomar» deja el foco en el h1 de la sección, no en <body>", async () => {
    const u = userEvent.setup();
    await abrirEnOtraPestana();
    await u.click(screen.getByRole("button", { name: "Retomar" }));
    const seccion = await titulo("Presupuesto");
    await waitFor(() => expect(seccion).toHaveFocus());
    expect(screen.queryByRole("alert")).toBeNull();
  });

  // La entrada real es `#/`, `#/inicio` o una ruta que no existe (también `#/pendientes`, retirada en F8), que REDIRIGEN con
  // `replace` a la Vista general: eso es la carga inicial, no un cambio de pantalla. El foco sigue en <body> y el primer Tab
  // es «Saltar».
  test.each([
    ["/pendientes", "Vista general", "/inicio/general"],
    ["/", "Vista general", "/inicio/general"],
    ["/inicio", "Vista general", "/inicio/general"],
    ["/no-existe", "Vista general", "/inicio/general"],
  ])("al cargar en %s no roba el foco: el primer Tab va a «Saltar al contenido»", async (entrada, h1, destino) => {
    const u = userEvent.setup();
    montar({ en: entrada });
    await titulo(h1);
    expect(ruta()).toBe(destino);
    await new Promise((r) => setTimeout(r, 120));
    expect(document.body).toHaveFocus();
    await u.tab();
    expect(screen.getByRole("button", { name: "Saltar al contenido" })).toHaveFocus();
  });

  // Acerca, en el armazón anterior: el h1 del esqueleto recibía el foco y la pantalla real lo sustituía, dejando el
  // foco en <body>.
  test("si la pantalla nueva pinta primero un esqueleto con h1, el foco va al h1 real", async () => {
    const u = userEvent.setup();
    function Lenta() {
      const [lista, setLista] = useState(false);
      useEffect(() => {
        const t = setTimeout(() => setLista(true), 60);
        return () => clearTimeout(t);
      }, []);
      return lista ? <h1>Simulador listo</h1> : <EsqueletoPagina titulo="Simulador de listas" />;
    }
    montar({ en: RUTA_DE_LA_MESA, paginas: conLaMesa(MesaQueVa, { simulador: Lenta }) });
    await u.click(await screen.findByRole("button", { name: "Ir al simulador" }));
    const real = await titulo("Simulador listo");
    await waitFor(() => expect(real).toHaveFocus());
  });
});

// Plan vial, Tarea 19: lo que la instalación apagó no se ofrece ni se abre por enlace directo.
describe("Marco: especialidades apagadas", () => {
  // F6, T2: «Riesgo» es una sección de la obra, así que su enlace directo es el de la obra (/riesgo sin obra redirige).
  test("con el riesgo apagado, abrir #/obra/.../riesgo por enlace directo dice que está apagado", async () => {
    apagar("riesgo");
    montar({ sesion: sesionDe("ana"), en: "/obra/empresa/7/riesgo" });
    expect(await screen.findByText(MENSAJE_APAGADO)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1, name: "Riesgo de la obra" })).toBeNull();
  });

  test("con el riesgo encendido, #/obra/.../riesgo abre su pantalla", async () => {
    apagar();
    montar({ sesion: sesionDe("ana"), en: "/obra/empresa/7/riesgo" });
    expect(await titulo("Riesgo de la obra")).toBeInTheDocument();
    expect(screen.queryByText(MENSAJE_APAGADO)).toBeNull();
  });

  test("con producción apagada, abrir una herramienta de Producción por enlace directo dice que está apagada", async () => {
    apagar("produccion");
    montar({ sesion: sesionDe("admin"), en: "/produccion/existencias" });
    expect(await screen.findByText(MENSAJE_APAGADO)).toBeInTheDocument();
    expect(await screen.findByText("Apagada")).toBeInTheDocument();
    expect(ruta()).toBe("/produccion/existencias");
    // El aviso es el único h1 de la pantalla (pasada en el navegador, H9): sin él la página quedaba sin título.
    expect(screen.getAllByRole("heading", { level: 1 })).toEqual([screen.getByRole("heading", { level: 1, name: "Apagada" })]);
  });

  test("con producción apagada, #/produccion no da vueltas: queda en la primera herramienta y dice que está apagada", async () => {
    apagar("produccion");
    montar({ sesion: sesionDe("admin"), en: "/produccion" });
    expect(await screen.findByText(MENSAJE_APAGADO)).toBeInTheDocument();
    expect(ruta()).toBe("/produccion/resumen");
    // La barra del espacio no ofrece pestañas que la cuenta no puede usar, y sin ninguna no se pinta vacía.
    expect(screen.queryByRole("navigation", { name: "Costos de producción" })).toBeNull();
    // La barra lateral tampoco ofrece Producción (el selector superior de ventana dedicada ya no existe).
    expect(within(screen.getByRole("complementary", { name: "Barra lateral" })).queryByRole("link", { name: /Producción/ })).toBeNull();
  });

  test("si no se puede leer el estado, nada se oculta (la API sigue cortando)", async () => {
    montar({ sesion: sesionDe("ana"), en: "/obra/empresa/7/riesgo" });
    expect(await titulo("Riesgo de la obra")).toBeInTheDocument();
  });
});

describe("Marco: barra lateral plegable (Reducir a iconos / Ampliar la barra y Ctrl+B)", () => {
  afterEach(() => {
    window.localStorage.removeItem("silice_sidebar_collapsed");
  });

  test("el botón de la barra lateral la pliega a riel compacto y el atajo Ctrl+B la vuelve a expandir", async () => {
    const usuario = userEvent.setup();
    montar({ en: "/inicio/pendientes" });
    await titulo("Pendientes");
    const lateral = screen.getByRole("complementary", { name: "Barra lateral" });
    expect(lateral).not.toHaveAttribute("data-collapsed", "true");
    await usuario.click(within(lateral).getByRole("button", { name: "Reducir a iconos" }));
    expect(lateral).toHaveAttribute("data-collapsed", "true");
    expect(window.localStorage.getItem("silice_sidebar_collapsed")).toBe("1");
    expect(within(lateral).getByRole("button", { name: "Ampliar la barra" })).toBeInTheDocument();
    await usuario.keyboard("{Control>}b{/Control}");
    expect(lateral).not.toHaveAttribute("data-collapsed", "true");
    expect(window.localStorage.getItem("silice_sidebar_collapsed")).toBe("0");
  });

  // Como en «el foco no se pierde cuando la acción quita el control»: el botón pulsado se desmonta (el riel y la barra
  // abierta son ramas distintas) y el foco caía en el cuerpo del documento (WCAG 2.4.3). Pasa al botón equivalente.
  test("con el teclado, «Reducir a iconos» deja el foco en «Ampliar la barra» y viceversa", async () => {
    const u = userEvent.setup();
    montar({ en: "/inicio/pendientes" });
    await titulo("Pendientes");
    const lateral = screen.getByRole("complementary", { name: "Barra lateral" });
    within(lateral).getByRole("button", { name: "Reducir a iconos" }).focus();
    await u.keyboard("{Enter}");
    expect(within(lateral).getByRole("button", { name: "Ampliar la barra" })).toHaveFocus();
    await u.keyboard("{Enter}");
    expect(within(lateral).getByRole("button", { name: "Reducir a iconos" })).toHaveFocus();
  });

  test("Ctrl+B con el foco en una obra de la lista lo deja en «Ampliar la barra», no en el cuerpo", async () => {
    const u = userEvent.setup();
    montar({ en: "/inicio/pendientes" });
    await titulo("Pendientes");
    const lateral = screen.getByRole("complementary", { name: "Barra lateral" });
    const lista = await within(lateral).findByRole("list", { name: "Obras" });
    within(lista).getAllByRole("link")[0]!.focus();
    await u.keyboard("{Control>}b{/Control}");
    expect(lateral).toHaveAttribute("data-collapsed", "true");
    expect(within(lateral).getByRole("button", { name: "Ampliar la barra" })).toHaveFocus();
  });

  test("Ctrl+B con el foco en el contenido no lo mueve", async () => {
    const u = userEvent.setup();
    montar({ en: "/inicio/pendientes" });
    await titulo("Pendientes");
    const contenido = document.getElementById("contenido")!;
    contenido.focus();
    await u.keyboard("{Control>}b{/Control}");
    expect(screen.getByRole("complementary", { name: "Barra lateral" })).toHaveAttribute("data-collapsed", "true");
    expect(contenido).toHaveFocus();
  });
});
