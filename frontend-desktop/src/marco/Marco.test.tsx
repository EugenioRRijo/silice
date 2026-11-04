import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useState } from "react";
import { MemoryRouter, useLocation, useNavigate } from "react-router";
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

function montar({ sesion = sesionDe("ana"), en = "/pendientes", paginas = ligeras(), canal }: Montaje = {}) {
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
const MENSAJE_APAGADO = "Esta función está apagada en esta instalación. Quien administra puede encenderla en Administración.";
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

describe("Marco: las rutas viejas llevan al marco nuevo", () => {
  test.each(["/", "/inicio", "/no-existe"])("%s acaba en #/pendientes, que muestra la bandeja", async (de) => {
    montar({ en: de });
    expect(await titulo("Pendientes")).toBeInTheDocument();
    expect(ruta()).toBe("/pendientes");
  });

  test("#/hoja con la obra 3 abierta en «Carpeta Sur.db» acaba en su Presupuesto", async () => {
    instalar(enSur);
    montar({ sesion: sesionConObra("3"), en: "/hoja" });
    expect(await titulo("Presupuesto")).toBeInTheDocument();
    expect(ruta()).toBe("/obra/Carpeta%20Sur.db/3/presupuesto");
  });

  test("#/hoja sin obra en la sesión acaba en #/pendientes", async () => {
    montar({ en: "/hoja" });
    expect(await titulo("Pendientes")).toBeInTheDocument();
    expect(ruta()).toBe("/pendientes");
  });

  test("una sección vieja con consulta y sin obra en la sesión se abre donde estaba (no pierde el envío)", async () => {
    montar({ en: "/aprobar?envio=12" });
    expect(await titulo("Aprobar una versión")).toBeInTheDocument();
    expect(ruta()).toBe("/aprobar?envio=12");
  });

  // T6 mueve estas dos a la Cuenta; hasta entonces siguen en /empresa/<entrada>.
  test.each([
    ["/administracion", "/empresa/personas"],
    ["/acerca", "/empresa/ayuda"],
  ])("%s acaba en %s", async (de, a) => {
    montar({ en: de });
    await waitFor(() => expect(ruta()).toBe(a));
  });

  test("#/simulador acaba en #/precios/simulador, dentro del marco nuevo", async () => {
    montar({ en: "/simulador" });
    expect(await titulo("Simulador de listas")).toBeInTheDocument();
    expect(ruta()).toBe("/precios/simulador");
    const barra = screen.getByRole("banner");
    expect(within(barra).getByRole("button", { name: "Buscar una obra, sección o pantalla… (Ctrl+K)" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Barra lateral" })).toBeInTheDocument();
    expect(within(barra).getByRole("navigation", { name: "Ruta" })).toHaveTextContent("Simulador de listas");
  });

  test("una entrada de Empresa que la cuenta no puede usar dice que no tiene permiso", async () => {
    montar({ en: "/empresa/personas" });
    expect(await screen.findByText("Su cuenta no tiene permiso para esta pantalla o acción.")).toBeInTheDocument();
  });
});

// F6, T4: Producción, Auditoría y Precios son espacios con su barra de herramientas (/<espacio>/<herramienta>). La tabla
// del contrato de rutas §2.4 (las filas que tocan a esos espacios) escrita a mano; destino final y consulta conservada.
describe("Marco: los espacios de Producción, Auditoría y Precios (F6, T4)", () => {
  const TABLA_2_4: readonly (readonly [string, string])[] = [
    ["/produccion", "/produccion/resumen"],
    ["/existencias", "/produccion/existencias"],
    ["/costos", "/produccion/costos"],
    ["/costo_tonelada", "/produccion/costo-tonelada"],
    ["/receta_planta", "/produccion/receta"],
    ["/producir_mezcla", "/produccion/mezcla"],
    ["/auditoria", "/auditoria/subir"],
    ["/libros", "/auditoria/libros"],
    ["/historial", "/auditoria/historial"],
    ["/precios_empresa", "/precios/listas"],
    ["/catalogo", "/precios/catalogo"],
    ["/indices", "/precios/indices"],
    ["/simulador", "/precios/simulador"],
    ["/empresa/precios", "/precios/catalogo"],
    ["/empresa/auditoria", "/auditoria/subir"],
    ["/empresa/produccion", "/produccion/existencias"],
  ];

  test.each(TABLA_2_4)("%s acaba en %s", async (de, a) => {
    montar({ en: de });
    await waitFor(() => expect(ruta()).toBe(a));
  });

  test.each(TABLA_2_4)("%s?proyecto=OF-001 acaba en %s?proyecto=OF-001 (conserva la consulta)", async (de, a) => {
    montar({ en: `${de}?proyecto=OF-001` });
    await waitFor(() => expect(ruta()).toBe(`${a}?proyecto=OF-001`));
  });

  test("#/aprobar?envio=12 sigue abriéndose donde estaba, como antes", async () => {
    montar({ en: "/aprobar?envio=12" });
    expect(await titulo("Aprobar una versión")).toBeInTheDocument();
    expect(ruta()).toBe("/aprobar?envio=12");
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
    const cabecera = screen.getByRole("region", { name: "Costos de producción" });
    expect(within(cabecera).queryByRole("heading")).toBeNull();
    expect(within(cabecera).getByText("Costos de producción")).toBeInTheDocument();
    const barra = screen.getByRole("navigation", { name: "Costos de producción" });
    expect(within(barra).queryByRole("heading")).toBeNull();
    // La cabecera va arriba de la barra y la barra, arriba de la pantalla.
    expect(cabecera.compareDocumentPosition(barra) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
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
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
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

  test("las migas dicen el espacio y la herramienta", async () => {
    montar({ en: "/auditoria/libros" });
    await titulo("Libro de la empresa");
    const migas = within(screen.getByRole("navigation", { name: "Ruta" }));
    expect(migas.getByText("Auditar un presupuesto")).toBeInTheDocument();
    expect(migas.getByText("Libro de la empresa")).toHaveAttribute("aria-current", "page");
  });

  test("la barra lateral marca el espacio abierto", async () => {
    montar({ en: "/auditoria/historial" });
    await titulo("Historial de auditorías");
    const lateral = screen.getByRole("complementary", { name: "Barra lateral" });
    expect(within(lateral).getByRole("link", { name: "Auditar un presupuesto" })).toHaveAttribute("aria-current", "page");
    expect(within(lateral).getByRole("link", { name: "Costos de producción" })).not.toHaveAttribute("aria-current");
  });

  test("Ctrl+K lleva a las rutas nuevas", async () => {
    const u = userEvent.setup();
    montar({ en: "/pendientes" });
    await titulo("Pendientes");
    await u.keyboard("{Control>}k{/Control}");
    await u.type(screen.getByRole("combobox", { name: "Buscar una obra, sección o pantalla" }), "existencias");
    await u.keyboard("{Enter}");
    await waitFor(() => expect(ruta()).toBe("/produccion/existencias"));
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

  test("dentro de una sección se ve la cabecera de la obra (nombre, moneda, versión), las migas y la página", async () => {
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
    const migas = within(screen.getByRole("navigation", { name: "Ruta" }));
    expect(migas.getByRole("link", { name: "Mis obras" })).toHaveAttribute("href", "/pendientes");
    expect(migas.getByRole("link", { name: "Galpón Sur" })).toHaveAttribute("href", "/obra/Carpeta%20Sur.db/3/resumen");
    expect(migas.getByText("Presupuesto")).toHaveAttribute("aria-current", "page");
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
    const barra = await screen.findByRole("navigation", { name: "Secciones de la obra" });
    await u.click(await within(barra).findByRole("link", { name: "Mercado" }));
    expect(await titulo("Estudio de mercado")).toBeInTheDocument();
    await new Promise((r) => setTimeout(r, 30));
    expect({
      fijadas: servidor.de("PUT", "/v1/sesion/proyecto").length,
      fichas: servidor.de("GET", "/v1/obras/resumen").length,
    }).toEqual({ fijadas: 1, fichas: 1 });
    await u.click(within(screen.getByRole("navigation", { name: "Secciones de la obra" })).getByRole("link", { name: "Resumen" }));
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
    expect(ruta()).toBe("/pendientes");
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
    await u.click(within(screen.getByRole("banner")).getByRole("link", { name: "Mis obras" }));
    await waitFor(() => expect(ruta()).toBe("/pendientes"));
    expect(await titulo("Pendientes")).toBeInTheDocument();
    await u.click(within(screen.getByRole("complementary", { name: "Barra lateral" })).getByRole("link", { name: "Precios y catálogo" }));
    await waitFor(() => expect(ruta()).toBe("/precios/catalogo"));
    expect(await screen.findByText("obra elegida: 7")).toBeInTheDocument();
  });
});

// F6, T5: la obra con su barra de secciones bajo la cabecera, las subvistas dentro de su sección y la barra lateral plana.
// Contrato de rutas 2.1 y 2.4 y diseño visual (2.2 y adenda A): oráculos escritos a mano.
describe("Marco: la barra de la obra y las subvistas (F6, T5)", () => {
  const barraDeLaObra = () => screen.getByRole("navigation", { name: "Secciones de la obra" });
  const textos = (nav: HTMLElement) => within(nav).getAllByRole("link").map((e) => e.textContent);
  const SEGUIDO = Node.DOCUMENT_POSITION_FOLLOWING;

  test("la barra de la obra va justo debajo de la cabecera, con las nueve secciones en orden y la actual marcada", async () => {
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    const cabecera = screen.getByRole("region", { name: "Obra abierta" });
    const barra = barraDeLaObra();
    expect(cabecera.nextElementSibling).toBe(barra);
    expect(barra.compareDocumentPosition(screen.getByRole("heading", { level: 1 })) & SEGUIDO).toBeTruthy();
    expect(barra.closest("main")).not.toBeNull();
    expect(textos(barra)).toEqual([
      "Resumen", "Presupuesto", "Tramos", "Archivos y planos", "Versiones", "Aprobaciones", "Mercado", "Control de obra", "Riesgo",
    ]);
    expect(within(barra).getAllByRole("link").map((e) => e.getAttribute("href"))).toEqual(
      ["resumen", "presupuesto", "tramos", "archivos", "versiones", "aprobaciones", "mercado", "control", "riesgo"].map((s) => `/obra/empresa/7/${s}`),
    );
    expect(within(barra).getAllByRole("link").filter((e) => e.getAttribute("aria-current") === "page").map((e) => e.textContent)).toEqual(["Presupuesto"]);
    expect(within(barra).queryByRole("heading")).toBeNull();
  });

  test("sin la obra lista (una que no existe) no hay cabecera ni barra de la obra", async () => {
    montar({ en: "/obra/empresa/99/resumen" });
    await titulo("Esa obra ya no existe");
    expect(screen.queryByRole("navigation", { name: "Secciones de la obra" })).toBeNull();
    expect(screen.queryByRole("region", { name: "Obra abierta" })).toBeNull();
  });

  test("quien solo revisa ve las secciones que puede usar, en el mismo orden (sin Tramos ni Control de obra)", async () => {
    montar({ sesion: sesionDe("rita"), en: "/obra/empresa/7/resumen" });
    await titulo("Resumen de la obra");
    expect(textos(barraDeLaObra())).toEqual(["Resumen", "Presupuesto", "Archivos y planos", "Versiones", "Aprobaciones", "Mercado", "Riesgo"]);
  });

  test("Riesgo solo se ofrece con su especialidad encendida", async () => {
    const encendida = montar({ en: "/obra/empresa/7/resumen" });
    await titulo("Resumen de la obra");
    expect(textos(barraDeLaObra())).toContain("Riesgo");
    encendida.unmount();
    apagar("riesgo");
    montar({ en: "/obra/empresa/7/resumen" });
    await titulo("Resumen de la obra");
    await waitFor(() => expect(textos(barraDeLaObra())).not.toContain("Riesgo"));
    expect(textos(barraDeLaObra())).toHaveLength(8);
  });

  test("Tramos sigue la especialidad vial: apagada, la sección no se ofrece", async () => {
    apagar("vial");
    montar({ en: "/obra/empresa/7/resumen" });
    await titulo("Resumen de la obra");
    await waitFor(() => expect(textos(barraDeLaObra())).not.toContain("Tramos"));
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
    expect(within(barraDeLaObra()).getByRole("link", { name: "Control de obra" })).toHaveAttribute("aria-current", "page");
    expect(within(barraDeLaObra()).getAllByRole("link").filter((e) => e.getAttribute("aria-current") === "page")).toHaveLength(1);
    const conmutador = screen.getByRole("navigation", { name: "Vistas de Control de obra" });
    expect(conmutador).toHaveClass("silice-barra-espacio--subvista");
    expect(within(conmutador).getAllByRole("link").map((e) => [e.textContent, e.getAttribute("href"), e.getAttribute("aria-current")])).toEqual([
      ["Control", "/obra/empresa/7/control", null],
      ["Reajuste", "/obra/empresa/7/control/reajuste", "page"],
      ["Escenarios", "/obra/empresa/7/control/escenarios", null],
    ]);
    // El conmutador va en el lienzo, debajo de la barra de la obra y encima de la pantalla; ninguna de las dos pone h1.
    expect(conmutador.closest("main")).not.toBeNull();
    expect(barraDeLaObra().compareDocumentPosition(conmutador) & SEGUIDO).toBeTruthy();
    expect(conmutador.compareDocumentPosition(screen.getByRole("heading", { level: 1 })) & SEGUIDO).toBeTruthy();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(within(conmutador).queryByRole("heading")).toBeNull();
  });

  test("en la pantalla principal de la sección el conmutador marca su raíz (Resumen y Tablero)", async () => {
    montar({ en: "/obra/empresa/7/resumen" });
    await titulo("Resumen de la obra");
    const conmutador = screen.getByRole("navigation", { name: "Vistas de Resumen" });
    expect(within(conmutador).getAllByRole("link").map((e) => [e.textContent, e.getAttribute("aria-current")])).toEqual([
      ["Resumen", "page"],
      ["Tablero", null],
    ]);
  });

  test.each([
    ["Vistas de Presupuesto", ["Partidas", "Componer"], "/obra/empresa/7/presupuesto"],
    ["Vistas de Aprobaciones", ["Aprobar", "Revisar un paquete", "Entregar"], "/obra/empresa/7/aprobaciones"],
    ["Vistas de Mercado", ["Estudio", "Actualizar precios"], "/obra/empresa/7/mercado"],
  ])("%s ofrece %j para quien puede usarlas todas", async (nombre, esperadas, en) => {
    const todo = sesionDe("ana", { acciones: [...ACCIONES.ana, "revisar_paquete"] });
    montar({ sesion: todo, en });
    await screen.findByRole("heading", { level: 1 });
    expect(textos(screen.getByRole("navigation", { name: nombre }))).toEqual(esperadas);
  });

  test("con una sola vista usable no se pinta el conmutador (rita no edita la hoja: Presupuesto queda con Partidas)", async () => {
    montar({ sesion: sesionDe("rita"), en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    expect(screen.queryByRole("navigation", { name: "Vistas de Presupuesto" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Componer" })).toBeNull();
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
    // Bajo la pestaña «Aprobaciones» de la obra; con una sola vista usable no hay conmutador.
    expect(within(barraDeLaObra()).getByRole("link", { name: "Aprobaciones" })).toHaveAttribute("aria-current", "page");
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
    expect(within(barraDeLaObra()).getByRole("link", { name: "Presupuesto" })).toBeInTheDocument();
  });

  test("las migas y el título del documento dicen la subvista", async () => {
    montar({ en: "/obra/empresa/7/control/reajuste" });
    await titulo("Reajuste de precios");
    expect(document.title).toBe("Reajuste · Control de obra · Casa Demo · Sílice");
    const migas = within(screen.getByRole("navigation", { name: "Ruta" }));
    expect(migas.getByRole("link", { name: "Control de obra" })).toHaveAttribute("href", "/obra/empresa/7/control");
    expect(migas.getByText("Reajuste")).toHaveAttribute("aria-current", "page");
  });

  test("cambiar de subvista con el conmutador deja el foco en el enlace pulsado (no se vuelve a montar)", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/control/reajuste" });
    await titulo("Reajuste de precios");
    const enlace = within(screen.getByRole("navigation", { name: "Vistas de Control de obra" })).getByRole("link", { name: "Escenarios" });
    await u.click(enlace);
    expect(await titulo("Escenarios de sensibilidad")).toBeInTheDocument();
    expect(ruta()).toBe("/obra/empresa/7/control/escenarios");
    const despues = within(screen.getByRole("navigation", { name: "Vistas de Control de obra" })).getByRole("link", { name: "Escenarios" });
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
    await u.click(within(screen.getByRole("navigation", { name: "Vistas de Control de obra" })).getByRole("link", { name: "Escenarios" }));
    await titulo("Escenarios de sensibilidad");
    await new Promise((r) => setTimeout(r, 30));
    expect({ fijadas: servidor.de("PUT", "/v1/sesion/proyecto").length, fichas: servidor.de("GET", "/v1/obras/resumen").length }).toEqual({ fijadas: 1, fichas: 1 });
  });
});

// Foco 3 de la revisión: los enlaces de las barras están dentro del lienzo, que el marco no intercepta; por eso la barra
// pregunta ella misma (como useNavegarSeguro). Pasar entre Partidas y Componer no pregunta: ProveedorDeLaHoja.test.tsx.
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
    const barra = screen.getByRole("navigation", { name: "Secciones de la obra" });
    await u.click(within(barra).getByRole("link", { name: "Mercado" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    expect(ruta()).toBe("/obra/empresa/7/presupuesto");
    await u.click(within(barra).getByRole("link", { name: "Mercado" }));
    await u.click(within(await screen.findByRole("dialog", { name: "Cambios sin guardar" })).getByRole("button", { name: "Salir y descartar" }));
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/7/mercado"));
  });

  test("con Componer a medio llenar, volver a Partidas desde el conmutador pregunta", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto/componer", paginas: ligeras({ componer: ComponerSucio }) });
    await titulo("Componer una partida");
    await u.click(within(screen.getByRole("navigation", { name: "Vistas de Presupuesto" })).getByRole("link", { name: "Partidas" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    expect(ruta()).toBe("/obra/empresa/7/presupuesto/componer");
  });

  test("sin nada que perder, la barra navega sin preguntar", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    await u.click(within(screen.getByRole("navigation", { name: "Secciones de la obra" })).getByRole("link", { name: "Versiones" }));
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

  test.each(TABLA_2_4_OBRA)("%s, sin obra en la sesión, acaba en #/pendientes", async (de) => {
    montar({ en: de });
    expect(await titulo("Pendientes")).toBeInTheDocument();
    expect(ruta()).toBe("/pendientes");
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
describe("Marco: elegir una obra en la barra lateral abre su Resumen (F6, T5)", () => {
  test("desde una subvista de una obra, elegir otra abre el Resumen de la otra", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/control/reajuste" });
    await titulo("Reajuste de precios");
    const lista = await screen.findByRole("list", { name: "Obras" });
    expect(within(lista).getByRole("link", { name: "Casa Demo" })).toHaveAttribute("aria-current", "page");
    expect(within(lista).getByRole("link", { name: "Torre B" })).not.toHaveAttribute("aria-current");
    await u.click(within(lista).getByRole("link", { name: "Torre B" }));
    expect(await titulo("Resumen de la obra")).toBeInTheDocument();
    expect(ruta()).toBe("/obra/empresa/8/resumen");
    expect(within(screen.getByRole("list", { name: "Obras" })).getByRole("link", { name: "Torre B" })).toHaveAttribute("aria-current", "page");
  });

  test("elegir la obra que ya está abierta, desde otra sección, lleva a su Resumen", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/versiones" });
    await titulo("Versiones");
    await u.click(within(await screen.findByRole("list", { name: "Obras" })).getByRole("link", { name: "Casa Demo" }));
    expect(await titulo("Resumen de la obra")).toBeInTheDocument();
    expect(ruta()).toBe("/obra/empresa/7/resumen");
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
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/8/resumen"));
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

  test("sin nada que perder, una obra de otra carpeta se abre sin preguntar", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto" });
    expect(await titulo("Presupuesto")).toBeInTheDocument();
    await u.click(await within(await screen.findByRole("list", { name: "Obras" })).findByRole("link", { name: "Galpón Sur" }));
    await waitFor(() => expect(ruta()).toBe("/obra/Carpeta%20Sur.db/3/resumen"));
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

  test("con un recorrido en curso su columna acompaña al contenido", async () => {
    iniciarRecorrido(RECORRIDO_AUDITAR);
    montar({ en: "/auditoria/libros" });
    await titulo("Libro de la empresa");
    expect(screen.getByRole("complementary", { name: "Recorrido" })).toBeInTheDocument();
  });

  test("Salir en el menú de la cuenta cierra el recorrido en curso y llama a alSalir", async () => {
    const u = userEvent.setup();
    iniciarRecorrido(RECORRIDO_AUDITAR);
    const { alSalir } = montar();
    await titulo("Pendientes");
    await u.click(screen.getByRole("button", { name: "Cuenta de Ana Pérez" }));
    await u.click(screen.getByRole("button", { name: "Salir" }));
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
    montar({ en: "/simulador", paginas: rota });
    expect(await screen.findByText("No se pudo abrir la pantalla")).toBeInTheDocument();
    expect(screen.getByRole("main")).not.toHaveTextContent(/página/i);
  });

  test("abrir otra carpeta desde una pantalla (Administración) avisa con su nombre, sin «carpeta de trabajo»", async () => {
    const u = userEvent.setup();
    function AbrirS2() {
      const { abrirCarpeta } = useAplicacion();
      return (
        <>
          <h1>Administración</h1>
          <button type="button" onClick={() => void abrirCarpeta?.("s2.db")}>
            Abrir s2
          </button>
        </>
      );
    }
    const admin = sesionDe("ana", { acciones: [...ACCIONES.ana, "administrar_cuentas"] });
    montar({ sesion: admin, en: "/empresa/personas", paginas: ligeras({ administracion: AbrirS2 }) });
    await u.click(await screen.findByRole("button", { name: "Abrir s2" }));
    expect(await screen.findByText("Ahora trabaja con la carpeta «s2».")).toBeInTheDocument();
    expect(servidor.de("POST", "/v1/casos/actual").map((l) => l.cuerpo)).toEqual([{ nombre: "s2.db" }]);
  });
});

describe("Marco: cuentas sin obras que leer", () => {
  // Pasada en el navegador del cierre de F2: el administrador (sin `leer_proyecto`) veía «No se pudieron cargar las
  // obras» porque el marco pedía `GET /v1/obras/todas` y la API contestaba 403. Sin el permiso no se pide (VB-9) y la
  // zona de obras no se pinta: lo que la cuenta no puede usar no aparece.
  test("sin leer_proyecto no pide las obras ni muestra la zona de obras con un error", async () => {
    const admin = sesionDe("admin");
    montar({ sesion: admin, en: "/empresa/ayuda" });
    await titulo("Acerca de Sílice");
    const lateral = screen.getByRole("complementary", { name: "Barra lateral" });
    expect(within(lateral).getByRole("link", { name: "Pendientes" })).toBeInTheDocument();
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
      ...oferta.secciones.map((s) => s.pagina),
      ...oferta.entradas.map((e) => e.pagina),
      ...oferta.sueltas.map((p) => p.id),
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
// pasa al único h1 de la nueva; si lo tiene un control que sigue (un enlace de la barra lateral o de las migas), no se
// toca; la carga inicial y sus redirecciones (`replace`) no lo roban; y el h1 de un esqueleto no lo retiene.
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

  test("un enlace de la barra lateral conserva el foco: solo se mueve si se perdió", async () => {
    const u = userEvent.setup();
    montar({ en: "/precios/simulador" });
    await titulo("Simulador de listas");
    const enlace = within(screen.getByRole("complementary", { name: "Barra lateral" })).getByRole("link", { name: "Pendientes" });
    await u.click(enlace);
    await titulo("Pendientes");
    await new Promise((r) => setTimeout(r, 80));
    expect(enlace).toHaveFocus();
  });

  test("un enlace de las migas que sigue tras navegar conserva el foco", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    const enlace = await within(screen.getByRole("navigation", { name: "Ruta" })).findByRole("link", { name: "Casa Demo" });
    await u.click(enlace);
    await titulo("Resumen de la obra");
    expect(ruta()).toBe("/obra/empresa/7/resumen");
    await new Promise((r) => setTimeout(r, 80));
    expect(enlace).toHaveFocus();
  });

  test("un enlace de las migas que desaparece al navegar («Mis obras») deja el foco en el h1 de la nueva", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("Presupuesto");
    await u.click(within(screen.getByRole("navigation", { name: "Ruta" })).getByRole("link", { name: "Mis obras" }));
    const nuevo = await titulo("Pendientes");
    expect(ruta()).toBe("/pendientes");
    expect(within(screen.getByRole("navigation", { name: "Ruta" })).queryByRole("link", { name: "Mis obras" })).toBeNull();
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

  // La entrada real es `#/pendientes`, o `#/`, `#/inicio` o una ruta que no existe, que REDIRIGEN con `replace` a
  // Pendientes: eso es la carga inicial, no un cambio de pantalla. El foco sigue en <body> y el primer Tab es «Saltar».
  test.each(["/pendientes", "/", "/inicio", "/no-existe"])("al cargar en %s no roba el foco: el primer Tab va a «Saltar al contenido»", async (entrada) => {
    const u = userEvent.setup();
    montar({ en: entrada });
    await titulo("Pendientes");
    expect(ruta()).toBe("/pendientes");
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
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
  });

  test("con producción apagada, #/produccion no da vueltas: queda en la primera herramienta y dice que está apagada", async () => {
    apagar("produccion");
    montar({ sesion: sesionDe("admin"), en: "/produccion" });
    expect(await screen.findByText(MENSAJE_APAGADO)).toBeInTheDocument();
    expect(ruta()).toBe("/produccion/resumen");
    // La barra del espacio no ofrece pestañas que la cuenta no puede usar, y sin ninguna no se pinta vacía.
    expect(screen.queryByRole("navigation", { name: "Costos de producción" })).toBeNull();
    // La barra lateral tampoco la ofrece.
    expect(within(screen.getByRole("complementary", { name: "Barra lateral" })).queryByRole("link", { name: "Costos de producción" })).toBeNull();
  });

  test("si no se puede leer el estado, nada se oculta (la API sigue cortando)", async () => {
    montar({ sesion: sesionDe("ana"), en: "/obra/empresa/7/riesgo" });
    expect(await titulo("Riesgo de la obra")).toBeInTheDocument();
  });
});
