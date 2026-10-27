import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect, useState } from "react";
import { MemoryRouter, useLocation, useNavigate } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../api/cliente";
import { EsqueletoPagina } from "../comun/EsqueletoPagina";
import type { SesionRespuesta } from "../api/tipos";
import { useAplicacion } from "../shell/contexto";
import { ACCIONES, caso, estadoInicial, json, ligeras, servidorFalso, sesionDe } from "../shell/obras/datosDePrueba";
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

describe("Marco: las rutas viejas llevan al marco nuevo", () => {
  test.each(["/", "/inicio", "/no-existe"])("%s acaba en #/pendientes, que muestra la mesa", async (de) => {
    montar({ en: de });
    expect(await titulo("Inicio de presupuestos y obras")).toBeInTheDocument();
    expect(ruta()).toBe("/pendientes");
  });

  test("#/hoja con la obra 3 abierta en «Carpeta Sur.db» acaba en su Presupuesto", async () => {
    instalar(enSur);
    montar({ sesion: sesionConObra("3"), en: "/hoja" });
    expect(await titulo("Hoja de la obra")).toBeInTheDocument();
    expect(ruta()).toBe("/obra/Carpeta%20Sur.db/3/presupuesto");
  });

  test("#/hoja sin obra en la sesión acaba en #/pendientes", async () => {
    montar({ en: "/hoja" });
    expect(await titulo("Inicio de presupuestos y obras")).toBeInTheDocument();
    expect(ruta()).toBe("/pendientes");
  });

  test("una sección vieja con consulta y sin obra en la sesión se abre donde estaba (no pierde el envío)", async () => {
    montar({ en: "/aprobar?envio=12" });
    expect(await titulo("Aprobar una versión")).toBeInTheDocument();
    expect(ruta()).toBe("/aprobar?envio=12");
  });

  test.each([
    ["/catalogo", "/empresa/precios"],
    ["/administracion", "/empresa/personas"],
    ["/acerca", "/empresa/ayuda"],
    ["/existencias", "/empresa/produccion"],
    ["/auditoria", "/empresa/auditoria"],
  ])("%s acaba en %s", async (de, a) => {
    montar({ en: de });
    await waitFor(() => expect(ruta()).toBe(a));
  });

  test("#/simulador sigue en #/simulador, dentro del marco nuevo", async () => {
    montar({ en: "/simulador" });
    expect(await titulo("Simulador de listas")).toBeInTheDocument();
    expect(ruta()).toBe("/simulador");
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

describe("Marco: la obra como espacio de trabajo", () => {
  function PaginaConObra() {
    const { proyecto, nombreProyecto } = useAplicacion();
    return (
      <>
        <h1>Hoja de la obra</h1>
        <p>{`obra de la página: ${proyecto ?? "ninguna"} (${nombreProyecto ?? "?"})`}</p>
      </>
    );
  }

  test("dentro de una sección se ve la cabecera de la obra (nombre, moneda, versión), las migas y la página", async () => {
    instalar(enSur);
    montar({ en: "/obra/Carpeta%20Sur.db/3/presupuesto", paginas: ligeras({ hoja: PaginaConObra }) });
    expect(await titulo("Hoja de la obra")).toBeInTheDocument();
    expect(screen.getByText("obra de la página: 3 (Galpón Sur)")).toBeInTheDocument();
    const cabecera = screen.getByRole("region", { name: "Obra abierta" });
    expect(within(cabecera).getByText("Galpón Sur")).toBeInTheDocument();
    await waitFor(() => expect(cabecera).toHaveTextContent("Moneda: USD"));
    expect(cabecera).toHaveTextContent("Versión: 002");
    const migas = within(screen.getByRole("navigation", { name: "Ruta" }));
    expect(migas.getByRole("link", { name: "Mis obras" })).toHaveAttribute("href", "/pendientes");
    expect(migas.getByRole("link", { name: "Galpón Sur" })).toHaveAttribute("href", "/obra/Carpeta%20Sur.db/3/resumen");
    expect(migas.getByText("Presupuesto")).toHaveAttribute("aria-current", "page");
    expect(document.title).toBe("Presupuesto · Galpón Sur · Sílice");
  });

  test("una obra sin versión guardada lo dice en la cabecera", async () => {
    montar({ en: "/obra/empresa/8/presupuesto" });
    expect(await titulo("Hoja de la obra")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Obra abierta" })).toHaveTextContent("Versión: sin versión guardada");
  });

  test("si otra pestaña abre otra obra, esta dice «Esta obra se abrió en otra pestaña», no monta la página y «Retomar» vuelve", async () => {
    const u = userEvent.setup();
    const canal: CanalDeObra = { onmessage: null, postMessage: vi.fn() };
    montar({ en: "/obra/empresa/7/presupuesto", canal });
    expect(await titulo("Hoja de la obra")).toBeInTheDocument();
    const fijadas = servidor.de("PUT", "/v1/sesion/proyecto").length;
    canal.onmessage?.({ data: { carpeta: SUR, obraId: 3 } } as MessageEvent);
    expect(await titulo("Esta obra se abrió en otra pestaña")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 1, name: "Hoja de la obra" })).toBeNull();
    await u.click(screen.getByRole("button", { name: "Retomar" }));
    expect(await titulo("Hoja de la obra")).toBeInTheDocument();
    expect(servidor.de("PUT", "/v1/sesion/proyecto").length).toBe(fijadas + 1);
  });

  test("un enlace viejo a una obra borrada dice «Esa obra ya no existe» con un enlace a Pendientes", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/99/resumen" });
    expect(await titulo("Esa obra ya no existe")).toBeInTheDocument();
    await u.click(screen.getByRole("link", { name: "Volver a Pendientes" }));
    expect(await titulo("Inicio de presupuestos y obras")).toBeInTheDocument();
    expect(ruta()).toBe("/pendientes");
  });

  test("la obra en que se entró queda elegida para las pantallas de fuera de la obra (Pendientes)", async () => {
    const u = userEvent.setup();
    function MesaConObra() {
      const { proyecto } = useAplicacion();
      return (
        <>
          <h1>Inicio de presupuestos y obras</h1>
          <p>{`obra elegida: ${proyecto ?? "ninguna"}`}</p>
        </>
      );
    }
    montar({ en: "/obra/empresa/7/resumen", paginas: ligeras({ obras: MesaConObra }) });
    expect(await screen.findByText("obra elegida: 7")).toBeInTheDocument();
    await u.click(within(screen.getByRole("banner")).getByRole("link", { name: "Mis obras" }));
    await waitFor(() => expect(ruta()).toBe("/pendientes"));
    expect(await screen.findByText("obra elegida: 7")).toBeInTheDocument();
  });
});

describe("Marco: cambiar de obra con cambios sin guardar (foco 5)", () => {
  function HojaSucia() {
    useFormularioSucio("hoja", true);
    return <h1>Hoja de la obra</h1>;
  }

  test("con la Hoja a medio llenar, elegir otra obra en el árbol pregunta; «Quedarme» deja la ruta igual", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto", paginas: ligeras({ hoja: HojaSucia }) });
    expect(await titulo("Hoja de la obra")).toBeInTheDocument();
    const arbol = await screen.findByRole("tree", { name: "Obras" });
    await u.click(await within(arbol).findByRole("treeitem", { name: "Torre B" }));
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    expect(pregunta).toHaveAccessibleDescription("Tiene cambios sin guardar en Hoja de la obra. Si sale de esta pantalla, se perderán.");
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    expect(screen.queryByRole("dialog", { name: "Cambios sin guardar" })).toBeNull();
    expect(ruta()).toBe("/obra/empresa/7/presupuesto");
    await u.click(within(arbol).getByRole("treeitem", { name: "Torre B" }));
    await u.click(within(await screen.findByRole("dialog", { name: "Cambios sin guardar" })).getByRole("button", { name: "Salir y descartar" }));
    await waitFor(() => expect(ruta()).toBe("/obra/empresa/8/resumen"));
  });

  test("con un borrador de la Hoja con cambios, ir a una obra de otra carpeta pregunta por él y «Quedarme» no cambia de carpeta", async () => {
    const u = userEvent.setup();
    instalar((estado) => {
      estado.borradores = [{ id: "b-1", proyecto: "7", version: "001", cambios: 2, rev: 3, tocado: "2026-10-27T10:00:00" }];
    });
    montar({ en: "/obra/empresa/7/presupuesto" });
    expect(await titulo("Hoja de la obra")).toBeInTheDocument();
    await u.click(await within(await screen.findByRole("tree", { name: "Obras" })).findByRole("treeitem", { name: "Galpón Sur" }));
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
    expect(await titulo("Hoja de la obra")).toBeInTheDocument();
    await u.click(await within(await screen.findByRole("tree", { name: "Obras" })).findByRole("treeitem", { name: "Galpón Sur" }));
    await waitFor(() => expect(ruta()).toBe("/obra/Carpeta%20Sur.db/3/resumen"));
    expect(screen.queryByRole("dialog", { name: "Cambios sin guardar" })).toBeNull();
    await waitFor(() => expect(servidor.de("POST", "/v1/casos/actual").map((l) => l.cuerpo)).toEqual([{ nombre: SUR }]));
  });
});

describe("Marco: lo que se monta con él", () => {
  test("Ctrl+K y el botón abren el buscador; Esc lo cierra y el foco vuelve al botón", async () => {
    const u = userEvent.setup();
    montar();
    await titulo("Inicio de presupuestos y obras");
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
    montar({ en: "/componer", paginas: ligeras({ componer: ComponerSucio }) });
    await titulo("Componer una partida");
    await u.keyboard("{Control>}k{/Control}");
    await u.type(screen.getByRole("combobox", { name: "Buscar una obra, sección o pantalla" }), "torre");
    await u.keyboard("{Enter}");
    const pregunta = await screen.findByRole("dialog", { name: "Cambios sin guardar" });
    await u.click(within(pregunta).getByRole("button", { name: "Quedarme" }));
    expect(ruta()).toBe("/componer");
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
    montar({ en: "/componer", paginas: ligeras({ componer: Pregunta }) });
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
    montar({ paginas: ligeras({ obras: MesaConNuevaObra }) });
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
    await titulo("Inicio de presupuestos y obras");
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
    montar({ en: "/libros" });
    await titulo("Libro de la empresa");
    expect(screen.getByRole("complementary", { name: "Recorrido" })).toBeInTheDocument();
  });

  test("Salir en el menú de la cuenta cierra el recorrido en curso y llama a alSalir", async () => {
    const u = userEvent.setup();
    iniciarRecorrido(RECORRIDO_AUDITAR);
    const { alSalir } = montar();
    await titulo("Inicio de presupuestos y obras");
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
    await titulo("Inicio de presupuestos y obras");
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
    await titulo("Hoja de la obra");
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
    ]);
    const usables = PAGINAS.filter((p) => usable(p, acciones, false)).map((p) => p.id);
    expect(usables.filter((id) => !alcanzables.has(id))).toEqual([]);
  });

  test("solo quien opera la arenera ve «Inicio de producción» en el buscador", () => {
    const deLaPagina = (acciones: readonly string[]) => ofertaDe(acciones, false).sueltas.map((p) => p.id);
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
        <button type="button" onClick={() => void ir("/simulador")}>
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
    ["Ir a la obra", "Hoja de la obra"],
  ])("«%s», un botón de la pantalla que navega, deja el foco en el único h1 de la nueva («%s»)", async (boton, h1) => {
    const u = userEvent.setup();
    montar({ paginas: ligeras({ obras: MesaQueVa }) });
    await u.click(await screen.findByRole("button", { name: boton }));
    const nuevo = await titulo(h1);
    await waitFor(() => expect(nuevo).toHaveFocus(), { timeout: 3000 });
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(nuevo).toHaveAttribute("tabindex", "-1");
  });

  test("un enlace de la barra lateral conserva el foco: solo se mueve si se perdió", async () => {
    const u = userEvent.setup();
    montar({ en: "/simulador" });
    await titulo("Simulador de listas");
    const enlace = within(screen.getByRole("complementary", { name: "Barra lateral" })).getByRole("link", { name: "Pendientes" });
    await u.click(enlace);
    await titulo("Inicio de presupuestos y obras");
    await new Promise((r) => setTimeout(r, 80));
    expect(enlace).toHaveFocus();
  });

  test("un enlace de las migas que sigue tras navegar conserva el foco", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("Hoja de la obra");
    const enlace = await within(screen.getByRole("navigation", { name: "Ruta" })).findByRole("link", { name: "Casa Demo" });
    await u.click(enlace);
    await titulo("Inicio de presupuestos y obras");
    expect(ruta()).toBe("/obra/empresa/7/resumen");
    await new Promise((r) => setTimeout(r, 80));
    expect(enlace).toHaveFocus();
  });

  test("un enlace de las migas que desaparece al navegar («Mis obras») deja el foco en el h1 de la nueva", async () => {
    const u = userEvent.setup();
    montar({ en: "/obra/empresa/7/presupuesto" });
    await titulo("Hoja de la obra");
    await u.click(within(screen.getByRole("navigation", { name: "Ruta" })).getByRole("link", { name: "Mis obras" }));
    const nuevo = await titulo("Inicio de presupuestos y obras");
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
    montar({ paginas: ligeras({ obras: MesaQueVa }) });
    await u.click(await screen.findByRole("button", { name: "Ir a la obra" }));
    const aviso = await titulo("No se pudo abrir la obra");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByText(TEXTO_DE_LA_CAIDA)).toBeInTheDocument();
    await waitFor(() => expect(aviso).toHaveFocus());
    caida.caido = false;
    await u.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await titulo("Hoja de la obra")).toBeInTheDocument();
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
    const seccion = await titulo("Hoja de la obra");
    await waitFor(() => expect(seccion).toHaveFocus());
    expect(screen.queryByRole("alert")).toBeNull();
  });

  // La entrada real es `#/pendientes`, o `#/`, `#/inicio` o una ruta que no existe, que REDIRIGEN con `replace` a
  // Pendientes: eso es la carga inicial, no un cambio de pantalla. El foco sigue en <body> y el primer Tab es «Saltar».
  test.each(["/pendientes", "/", "/inicio", "/no-existe"])("al cargar en %s no roba el foco: el primer Tab va a «Saltar al contenido»", async (entrada) => {
    const u = userEvent.setup();
    montar({ en: entrada });
    await titulo("Inicio de presupuestos y obras");
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
    montar({ paginas: ligeras({ obras: MesaQueVa, simulador: Lenta }) });
    await u.click(await screen.findByRole("button", { name: "Ir al simulador" }));
    const real = await titulo("Simulador listo");
    await waitFor(() => expect(real).toHaveFocus());
  });
});
