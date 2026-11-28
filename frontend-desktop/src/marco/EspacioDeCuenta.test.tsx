import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { fijarCsrf } from "../api/cliente";
import type { SesionRespuesta } from "../api/tipos";
import { CLAVE_TAMANO_LETRA } from "../comun/preferenciaDeLetra";
import { useAplicacion } from "../shell/contexto";
import { AyudaDeSilice } from "../comun/ayuda/AyudaDeSilice";
import { ACCIONES, caso, estadoInicial, ligeras, servidorFalso, sesionDe } from "../shell/obras/datosDePrueba";
import { RECORRIDO_AUDITAR, recorridoEnCurso, terminarRecorrido } from "../shell/recorrido";
import type { PaginaDef } from "../shell/rutas";
import { cancelarSalida } from "../shell/salida";
import { olvidarFormularios } from "../shell/sucio";
import { Marco } from "./Marco";

// Plan F6, T6: la Cuenta es un espacio con su cabecera (la persona y «Salir de la sesión») y su barra de secciones
// (/cuenta/:seccion). Oráculo escrito a mano: contrato de rutas 2026-11-04 §3 (quién ve qué) y diseño visual §2.3, §2.4-E
// y adenda C. Las pantallas de administración y «Acerca de» son ligeras: aquí se vigila lo que pone el marco.

const SUR = "Carpeta Sur.db";
const TITULOS = {
  preferencias: "Configuración",
  contrasena: "Contraseña",
  // C11b: qué notificaciones recibe; toda cuenta la tiene, como Configuración y Contraseña.
  notificaciones: "Notificaciones",
  cuentas: "Cuentas y permisos",
  empresa: "Empresa y tema",
  carpetas: "Carpetas",
  sistema: "Especialidades, IA e instalación",
  ayuda: "Ayuda y acerca de Sílice",
} as const;
const TODAS = Object.values(TITULOS);
const RUTAS = Object.keys(TITULOS).map((id) => `/cuenta/${id}`);
const SOLO_DOS = [TITULOS.preferencias, TITULOS.contrasena, TITULOS.notificaciones, TITULOS.ayuda];
const MENSAJE_SIN_PERMISO = "Su cuenta no tiene permiso para esta pantalla o acción.";
const CONTENIDO = "Contenido de administración";
const JERGA = /módulo|área|página|carpeta de trabajo|streamlit/i;

let servidor: ReturnType<typeof servidorFalso>;

beforeEach(() => {
  const estado = estadoInicial();
  estado.casos = [...estado.casos, caso(SUR)];
  servidor = servidorFalso(estado);
  vi.stubGlobal("fetch", vi.fn(servidor.fetchFalso));
  fijarCsrf("tok");
});
afterEach(() => {
  cancelarSalida();
  olvidarFormularios();
  terminarRecorrido();
  vi.unstubAllGlobals();
  fijarCsrf(null);
  document.documentElement.removeAttribute("data-silice-letra");
  window.localStorage.removeItem(CLAVE_TAMANO_LETRA);
});

function Ubicacion() {
  const { pathname, search } = useLocation();
  return <output data-testid="ruta">{`${pathname}${search}`}</output>;
}
const ruta = () => screen.getByTestId("ruta").textContent;

// La administración ligera no trae h1 (en el real, lo pone el marco); «Acerca de» sí, como el real.
const ADMINISTRACION = () => <p>{CONTENIDO}</p>;

function montar({ sesion = sesionDe("admin"), en = "/cuenta/preferencias", paginas = ligeras({ administracion: ADMINISTRACION }) }: { sesion?: SesionRespuesta; en?: string; paginas?: readonly PaginaDef[] } = {}) {
  const alSalir = vi.fn();
  const alExpirar = vi.fn();
  const vista = render(
    <MemoryRouter initialEntries={[en]}>
      <Marco sesion={sesion} alSalir={alSalir} alExpirar={alExpirar} paginas={paginas} />
      <Ubicacion />
    </MemoryRouter>,
  );
  return { ...vista, alSalir, alExpirar };
}

const barra = () => screen.findByRole("navigation", { name: "Secciones de la cuenta" });
const conAcciones = (acciones: readonly string[]) => sesionDe("ana", { acciones: [...acciones] });
const sinCambiarDeCarpeta = ACCIONES.admin.filter((a) => a !== "cambiar_caso");

describe("la Cuenta: qué secciones ve cada cuenta (contrato §3)", () => {
  const PERFILES: readonly (readonly [string, readonly string[], readonly string[]])[] = [
    ["quien arma y puede cambiar de carpeta, pero no administra", ACCIONES.ana, SOLO_DOS],
    ["quien solo revisa", ACCIONES.rita, SOLO_DOS],
    ["quien administra y puede cambiar de carpeta", ACCIONES.admin, TODAS],
    ["quien administra pero no puede cambiar de carpeta", sinCambiarDeCarpeta, TODAS.filter((t) => t !== TITULOS.carpetas)],
    ["quien puede cambiar de carpeta sin administrar", ["leer_proyecto", "cambiar_caso"], SOLO_DOS],
    ["quien solo puede encender especialidades", ["activar_modulos"], SOLO_DOS],
  ];

  test.each(PERFILES)("%s", async (_, acciones, esperadas) => {
    montar({ sesion: conAcciones(acciones) });
    const enlaces = within(await barra()).getAllByRole("link");
    expect(enlaces.map((e) => e.textContent)).toEqual(esperadas);
    const rutas = Object.fromEntries(Object.entries(TITULOS).map(([id, titulo]) => [titulo, `/cuenta/${id}`]));
    expect(enlaces.map((e) => e.getAttribute("href"))).toEqual(esperadas.map((t) => rutas[t]));
    expect(enlaces.filter((e) => e.getAttribute("aria-current") === "page").map((e) => e.textContent)).toEqual([TITULOS.preferencias]);
  });

  test.each([
    ["quien solo revisa", ACCIONES.rita, "/cuenta/cuentas", TITULOS.cuentas],
    ["quien solo revisa", ACCIONES.rita, "/cuenta/empresa", TITULOS.empresa],
    ["quien solo revisa", ACCIONES.rita, "/cuenta/sistema", TITULOS.sistema],
    ["quien solo revisa", ACCIONES.rita, "/cuenta/carpetas", TITULOS.carpetas],
    ["quien arma y cambia de carpeta", ACCIONES.ana, "/cuenta/carpetas", TITULOS.carpetas],
    ["quien administra sin cambiar de carpeta", sinCambiarDeCarpeta, "/cuenta/carpetas", TITULOS.carpetas],
  ])("%s, con %s escrita a mano, ve «Sin permiso» y no la pantalla", async (_, acciones, direccion, noOfrecida) => {
    montar({ sesion: conAcciones(acciones), en: direccion });
    expect(await screen.findByText("Sin permiso")).toBeInTheDocument();
    expect(screen.getByText(MENSAJE_SIN_PERMISO)).toBeInTheDocument();
    expect(screen.queryByText(CONTENIDO)).toBeNull();
    expect(ruta()).toBe(direccion);
    // La barra sigue arriba con lo que sí puede usar, y la pantalla tiene su único h1.
    const enlaces = within(await barra()).getAllByRole("link");
    expect(enlaces.map((e) => e.textContent)).not.toContain(noOfrecida);
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    // El h1 es el de la sección; el aviso va un nivel más abajo, para que la pantalla no tenga dos (H9).
    expect(screen.getByRole("heading", { level: 2, name: "Sin permiso" })).toBeInTheDocument();
  });

  test("quien administra y cambia de carpeta abre las cuatro secciones de administración", async () => {
    for (const seccion of ["cuentas", "empresa", "carpetas", "sistema"]) {
      const { unmount } = montar({ en: `/cuenta/${seccion}` });
      expect(await screen.findByText(CONTENIDO)).toBeInTheDocument();
      expect(screen.queryByText("Sin permiso")).toBeNull();
      unmount();
    }
  });
});

describe("la Cuenta: dirección, cabecera y un solo h1", () => {
  test("/cuenta lleva a /cuenta/preferencias conservando la consulta", async () => {
    montar({ sesion: sesionDe("rita"), en: "/cuenta?proyecto=OF-001" });
    await waitFor(() => expect(ruta()).toBe("/cuenta/preferencias?proyecto=OF-001"));
  });

  test("una sección que no existe lleva a /cuenta/preferencias, con replace y conservando la consulta", async () => {
    montar({ sesion: sesionDe("rita"), en: "/cuenta/xyz?proyecto=OF-001" });
    await waitFor(() => expect(ruta()).toBe("/cuenta/preferencias?proyecto=OF-001"));
    expect(await screen.findByRole("heading", { level: 1, name: TITULOS.preferencias })).toBeInTheDocument();
  });

  test("la cabecera dice quién es la persona y su rol, sin encabezado, y «Salir de la sesión» sale", async () => {
    const u = userEvent.setup();
    const { alSalir } = montar({ sesion: sesionDe("ana"), en: "/cuenta/ayuda" });
    const cabecera = await screen.findByRole("region", { name: "Cuenta" });
    expect(within(cabecera).getByText("AP")).toHaveAttribute("aria-hidden", "true");
    expect(within(cabecera).getByText("Ana Pérez")).toBeInTheDocument();
    expect(within(cabecera).getByText("ana · arma presupuestos (arma)")).toBeInTheDocument();
    expect(within(cabecera).queryByRole("heading")).toBeNull();
    await u.click(within(cabecera).getByRole("button", { name: "Salir de la sesión" }));
    expect(alSalir).toHaveBeenCalledTimes(1);
  });

  test.each(Object.entries(TITULOS))("%s tiene un único h1, «%s», y el título del documento lo dice", async (id, titulo) => {
    montar({ en: `/cuenta/${id}` });
    const h1 = await screen.findByRole("heading", { level: 1, name: titulo }, { timeout: 3000 });
    expect(screen.getAllByRole("heading", { level: 1 })).toEqual([h1]);
    // El título del documento no repite el nombre del producto cuando el título ya lo trae (comun/tituloDelDocumento).
    expect(document.title).toBe(titulo.includes("Sílice") ? titulo : `${titulo} · Sílice`);
  });

  test("ninguna sección dice «módulo», «área», «página», «carpeta de trabajo» ni «Streamlit»", async () => {
    for (const direccion of RUTAS) {
      const { unmount } = montar({ en: direccion });
      await barra();
      await screen.findAllByRole("heading", { level: 1 }, { timeout: 3000 });
      expect(document.body.textContent, direccion).not.toMatch(JERGA);
      unmount();
    }
  });
});

describe("la Cuenta: Configuración (adenda C)", () => {
  test("toda cuenta tiene el tamaño de letra aquí y ya no en la barra de arriba", async () => {
    for (const rol of ["rita", "ana", "admin"] as const) {
      const { unmount } = montar({ sesion: sesionDe(rol) });
      const grupo = await screen.findByRole("group", { name: "Tamaño de letra" });
      expect(screen.getByRole("main")).toContainElement(grupo);
      expect(within(screen.getByRole("banner")).queryByRole("group", { name: "Tamaño de letra" })).toBeNull();
      unmount();
    }
  });

  test("elegir «Grande» cambia la letra y se recuerda", async () => {
    const u = userEvent.setup();
    montar({ sesion: sesionDe("rita") });
    const grupo = await screen.findByRole("group", { name: "Tamaño de letra" });
    await u.click(within(grupo).getByRole("button", { name: "Grande" }));
    expect(document.documentElement.dataset.siliceLetra).toBe("grande");
    expect(within(grupo).getByRole("button", { name: "Grande" })).toHaveAttribute("aria-pressed", "true");
    expect(window.localStorage.getItem(CLAVE_TAMANO_LETRA)).toBe("grande");
  });

  test("trae una muestra de lectura y los datos de la cuenta", async () => {
    montar({ sesion: sesionDe("ana") });
    await screen.findByRole("group", { name: "Tamaño de letra" });
    expect(screen.getByText(/Partida C-001 · Vaciado de concreto/)).toBeInTheDocument();
    const datos = screen.getByRole("region", { name: "Datos de la cuenta" });
    expect(within(datos).getAllByRole("term").map((t) => t.textContent)).toEqual(["Nombre", "Usuario", "Rol"]);
    expect(within(datos).getAllByRole("definition").map((d) => d.textContent)).toEqual(["Ana Pérez", "ana", "arma presupuestos (arma)"]);
  });
});

describe("la Cuenta: Ayuda y recorridos guiados", () => {
  test("el recorrido de auditoría empieza desde la Ayuda y lleva a su primera pantalla", async () => {
    const u = userEvent.setup();
    montar({ sesion: sesionDe("rita"), en: "/cuenta/ayuda" });
    await screen.findByRole("heading", { level: 2, name: "Recorridos guiados" });
    expect(recorridoEnCurso()).toBeNull();
    await u.click(screen.getByRole("button", { name: /Auditar un libro de la empresa/ }));
    await waitFor(() => expect(ruta()).toBe("/auditoria/subir"));
    expect(recorridoEnCurso()).toBe(RECORRIDO_AUDITAR);
  });

  test("con ?tema=recorridos el foco llega al título de los recorridos guiados", async () => {
    montar({ sesion: sesionDe("rita"), en: "/cuenta/ayuda?tema=recorridos", paginas: ligeras({ acerca: AyudaDeSilice }) });
    const titulo = await screen.findByRole("heading", { level: 2, name: "Recorridos guiados" });
    await waitFor(() => expect(titulo).toHaveFocus());
  });
});

describe("la Cuenta: al cambiar de carpeta se vuelve a Carpetas", () => {
  function AbrirOtra() {
    const { abrirCarpeta } = useAplicacion();
    return (
      <>
        <p>{CONTENIDO}</p>
        <button type="button" onClick={() => void abrirCarpeta?.(SUR)}>
          Abrir la otra
        </button>
      </>
    );
  }

  test("abrir otra carpeta deja la pantalla en /cuenta/carpetas, vuelta a montar, con el aviso", async () => {
    const u = userEvent.setup();
    montar({ en: "/cuenta/carpetas", paginas: ligeras({ administracion: AbrirOtra }) });
    await u.click(await screen.findByRole("button", { name: "Abrir la otra" }));
    expect(await screen.findByText("Ahora trabaja con la carpeta «Carpeta Sur».")).toBeInTheDocument();
    expect(servidor.de("POST", "/v1/casos/actual").map((l) => l.cuerpo)).toEqual([{ nombre: SUR }]);
    expect(ruta()).toBe("/cuenta/carpetas");
    expect(await screen.findByRole("button", { name: "Abrir la otra" })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});

// C10: la actividad de una cuenta (`/cuenta/actividad?usuario=<login>`). No es una pestaña: la barra sigue siendo la de siempre.
describe("la Cuenta: la actividad de una persona", () => {
  const ACTIVIDAD = {
    usuario: "ana",
    desde: "2026-10-01",
    hasta: "2026-10-31",
    dias: [{ fecha: "2026-10-19", cuantos: 1 }],
    cifras: { versiones_guardadas: 1, versiones_enviadas: 0, dictamenes: 0, auditorias: 0 },
    eventos: [{ fecha: "2026-10-19T09:00:00", tipo: "version_guardada", obra: "Vivienda Demo", archivo: "", texto: "guardó la versión V1 de Vivienda Demo" }],
    recortado: false,
  };
  let pedidas: string[];
  let contestar: () => Response;

  beforeEach(() => {
    pedidas = [];
    contestar = () => new Response(JSON.stringify(ACTIVIDAD), { status: 200, headers: { "Content-Type": "application/json" } });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (entrada: RequestInfo | URL, init?: RequestInit) => {
        const url = String(entrada);
        if (!url.startsWith("/v1/actividad")) return servidor.fetchFalso(entrada, init);
        pedidas.push(url);
        return contestar();
      }),
    );
  });

  test("abre con su h1, el calendario y la barra de la Cuenta con «Configuración» marcada", async () => {
    montar({ sesion: sesionDe("ana"), en: "/cuenta/actividad?usuario=ana" });
    expect(await screen.findByRole("heading", { level: 1, name: "Actividad de ana" })).toBeInTheDocument();
    expect(await screen.findByRole("group", { name: /Calendario de actividad/ })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    const enlaces = within(await barra()).getAllByRole("link");
    expect(enlaces.map((e) => e.textContent)).toEqual(SOLO_DOS);
    expect(enlaces.filter((e) => e.getAttribute("aria-current") === "page").map((e) => e.textContent)).toEqual([TITULOS.preferencias]);
    expect(pedidas).toEqual(["/v1/actividad?usuario=ana"]);
  });

  test("sin usuario en la consulta es la propia cuenta", async () => {
    montar({ sesion: sesionDe("rita"), en: "/cuenta/actividad" });
    expect(await screen.findByRole("heading", { level: 1, name: "Actividad de rita" })).toBeInTheDocument();
    await screen.findByRole("group", { name: /Calendario de actividad/ });
    expect(pedidas).toEqual(["/v1/actividad?usuario=rita"]);
    expect(ruta()).toBe("/cuenta/actividad");
  });

  test("quien administra y mira a otra persona tiene marcada «Cuentas y permisos»", async () => {
    montar({ en: "/cuenta/actividad?usuario=ana" });
    expect(await screen.findByRole("heading", { level: 1, name: "Actividad de ana" })).toBeInTheDocument();
    const enlaces = within(await barra()).getAllByRole("link");
    expect(enlaces.filter((e) => e.getAttribute("aria-current") === "page").map((e) => e.textContent)).toEqual([TITULOS.cuentas]);
  });

  test("quien administra y mira la suya tiene marcada «Configuración»", async () => {
    montar({ en: "/cuenta/actividad?usuario=admin" });
    await screen.findByRole("heading", { level: 1, name: "Actividad de admin" });
    const enlaces = within(await barra()).getAllByRole("link");
    expect(enlaces.filter((e) => e.getAttribute("aria-current") === "page").map((e) => e.textContent)).toEqual([TITULOS.preferencias]);
  });

  test("si el servidor no deja ver esa cuenta, la pantalla dice el motivo y no pinta el calendario", async () => {
    contestar = () => new Response(JSON.stringify({ detalle: "Solo puede ver su propia actividad, o la de todos si administra las cuentas." }), { status: 403, headers: { "Content-Type": "application/json" } });
    montar({ sesion: sesionDe("ana"), en: "/cuenta/actividad?usuario=rita" });
    expect(await screen.findByRole("alert")).toHaveTextContent("Solo puede ver su propia actividad, o la de todos si administra las cuentas.");
    expect(screen.queryByRole("group", { name: /Calendario de actividad/ })).toBeNull();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });

  test("«Configuración» ofrece «Ver mi actividad», que lleva a la propia", async () => {
    const u = userEvent.setup();
    montar({ sesion: sesionDe("ana"), en: "/cuenta/preferencias" });
    const enlace = await screen.findByRole("link", { name: "Ver mi actividad" });
    expect(enlace).toHaveAttribute("href", "/cuenta/actividad?usuario=ana");
    await u.click(enlace);
    expect(await screen.findByRole("heading", { level: 1, name: "Actividad de ana" })).toBeInTheDocument();
    expect(ruta()).toBe("/cuenta/actividad?usuario=ana");
  });
});
