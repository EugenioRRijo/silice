import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useNavigate, type NavigateFunction } from "react-router";
import { afterEach, beforeEach, describe, expect, onTestFinished, test, vi } from "vitest";
import { fijarCsrf } from "../api/cliente";
import type { SesionRespuesta } from "../api/tipos";
import { alertaConTexto } from "../test/ayudas";
import { useState, useEffect } from "react";
import { useAplicacion } from "./contexto";
import { EsqueletoPagina } from "../comun/EsqueletoPagina";
import { RECORRIDO_AUDITAR, iniciarRecorrido, recorridoEnCurso, terminarRecorrido } from "./recorrido";
import { Shell } from "./Shell";
import { cancelarSalida } from "./salida";
import { formulariosSucios, olvidarFormularios, useFormularioSucio } from "./sucio";
import { PAGINAS as REGISTRO } from "./rutas";
import type { ModuloId, PaginaDef } from "./rutas";

function json(cuerpo: unknown, estado = 200): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });
}

const ACCIONES_ARMA = ["editar_hoja", "leer_proyecto", "cambiar_caso", "entregar_paquete"];

function sesionCon(parcial: Partial<SesionRespuesta> = {}): SesionRespuesta {
  return {
    login: "ana",
    nombre: "Ana Pérez",
    roles: ["arma"],
    csrf: "tok",
    debe_cambiar_clave: false,
    acciones: ACCIONES_ARMA,
    modo_entrega: false,
    ...parcial,
  };
}

function PaginaA() {
  const { proyecto, caso } = useAplicacion();
  return (
    <div>
      <h1>Pantalla del tablero</h1>
      <p>proyecto={proyecto ?? "ninguno"}</p>
      <p>caso={caso?.nombre ?? "?"}</p>
    </div>
  );
}

function PaginaB() {
  return <h1>Otra pantalla</h1>;
}

const CARGAR_B = async () => ({ default: PaginaB });

function InicioDeObras() {
  return <h1>Inicio de presupuestos y obras</h1>;
}

// Registro de prueba: cada pantalla con su modulo y su area (plan de modulos, MOD-1). El orden decide el de los paneles.
const PAGINAS: PaginaDef[] = [
  { id: "tablero", titulo: "Tablero del proyecto", enUnaLinea: "Cómo va el proyecto", seccion: "Trabajo", accion: "leer_proyecto", ubicacion: { modulo: "obras", area: "obras" }, cargar: async () => ({ default: PaginaA }) },
  { id: "hoja", titulo: "Hoja del proyecto", enUnaLinea: "Pantalla de prueba", seccion: "Trabajo", accion: "editar_hoja", ubicacion: { modulo: "obras", area: "obras" }, cargar: CARGAR_B },
  { id: "catalogo", titulo: "Catálogo de partidas e insumos", enUnaLinea: "Pantalla de prueba", seccion: "Trabajo", accion: "leer_proyecto", ubicacion: { modulo: "obras", area: "partidas" }, cargar: CARGAR_B },
  { id: "control", titulo: "Control de obra", enUnaLinea: "Pantalla de prueba", seccion: "Trabajo", accion: "control_de_obra", ubicacion: { modulo: "obras", area: "control" }, cargar: CARGAR_B },
  { id: "acerca", titulo: "Acerca de Sílice", enUnaLinea: "Pantalla de prueba", seccion: "Trabajo", accion: null, ubicacion: null, cargar: CARGAR_B },
  { id: "revisar", titulo: "Revisar un paquete", enUnaLinea: "Pantalla de prueba", seccion: "Revisión", accion: "revisar_paquete", ubicacion: { modulo: "auditoria", area: "paquetes" }, cargar: CARGAR_B },
  { id: "escenarios", titulo: "Escenarios de sensibilidad", enUnaLinea: "Pantalla de prueba", seccion: "Investigación", accion: "editar_hoja", ubicacion: { modulo: "obras", area: "control" }, cargar: CARGAR_B },
  { id: "obras", titulo: "Inicio de presupuestos y obras", enUnaLinea: "Pantalla de prueba", seccion: "Trabajo", accion: null, ubicacion: { modulo: "obras", area: "inicio" }, cargar: async () => ({ default: InicioDeObras }) },
];

// Las 22 pantallas del registro, cada una con un h1 con su titulo (sin bajar la pagina real).
const LIGERAS: PaginaDef[] = REGISTRO.map((p) => {
  const Ligera = () => <h1>{p.titulo}</h1>;
  return { ...p, cargar: async () => ({ default: Ligera }) };
});

// Acciones por rol, escritas a mano desde PERMISOS de seguridad/permisos.py (ana arma, rita revisa, admin administra).
const ACCIONES_POR_ROL: Record<"ana" | "rita" | "admin", string[]> = {
  ana: [
    "editar_hoja",
    "convertir_y_reajustar",
    "control_de_obra",
    "decidir_recuperacion",
    "entregar_paquete",
    "operar_arenera",
    "leer_proyecto",
    "aprobar_version",
    "cambiar_caso",
  ],
  rita: ["leer_proyecto", "revisar_paquete", "aprobar_version"],
  admin: [
    "operar_arenera",
    "cambiar_caso",
    "administrar_cuentas",
    "administrar_empresa",
    "administrar_precios",
    "administrar_red_y_api",
    "cambiar_carpeta_de_datos",
  ],
};

const CASOS = {
  actual: { nombre: "clinica", ruta_relativa: "data/clinica.db" },
  casos: [
    { nombre: "clinica", ruta_relativa: "data/clinica.db" },
    { nombre: "arenaza", ruta_relativa: "data/arenaza.db" },
  ],
};

const PROYECTOS = [
  { codigo: "P-01", nombre: "Clínica Norte", version_vigente: 3, actualizado: "2026-10-01" },
  { codigo: "P-02", nombre: "Galpón", version_vigente: null, actualizado: null },
];

describe("Shell", () => {
  const fetchFalso = vi.fn<typeof fetch>();
  let alSalir: ReturnType<typeof vi.fn<() => void>>;
  let alExpirar: ReturnType<typeof vi.fn<() => void>>;
  let casos = CASOS;

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchFalso);
    fetchFalso.mockReset();
    fijarCsrf("tok");
    casos = CASOS;
    fetchFalso.mockImplementation(async (entrada, init) => {
      const ruta = String(entrada);
      const metodo = init?.method ?? "GET";
      if (ruta === "/v1/casos" && metodo === "GET") return json(casos);
      if (ruta === "/v1/casos/actual" && metodo === "POST") {
        const { nombre } = JSON.parse(String(init?.body)) as { nombre: string };
        const elegido = CASOS.casos.find((c) => c.nombre === nombre);
        if (!elegido) return json({ detalle: "No existe ese caso." }, 404);
        casos = { ...CASOS, actual: elegido };
        return json({ actual: elegido });
      }
      if (ruta === "/v1/proyectos") return json(PROYECTOS);
      if (ruta === "/v1/sesion/preferencias" && metodo === "PUT") return new Response(null, { status: 204 });
      return json({ detalle: "No encontrado." }, 404);
    });
    alSalir = vi.fn<() => void>();
    alExpirar = vi.fn<() => void>();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function montar(sesion = sesionCon(), ruta = "/tablero", paginas: readonly PaginaDef[] = PAGINAS) {
    return render(
      <MemoryRouter initialEntries={[ruta]}>
        <Shell sesion={sesion} alSalir={alSalir} alExpirar={alExpirar} paginas={paginas} />
      </MemoryRouter>,
    );
  }

  // La barra superior y el sidebar de modulos (en capa: un dialogo; fijado: una navegacion) tienen nombre propio.
  function menu() {
    return screen.getByRole("navigation", { name: "Menú principal" });
  }

  function sidebar() {
    return screen.getByRole("dialog", { name: "Módulos de Sílice" });
  }

  async function abrirModulos(usuario: ReturnType<typeof userEvent.setup>) {
    await usuario.click(screen.getByRole("button", { name: "Sílice, abrir los módulos" }));
    return sidebar();
  }

  // Las pantallas de la seccion «Areas de …» del sidebar (la que se ve cuando la barra no cabe).
  function areasDelSidebar(): HTMLElement {
    return sidebar().querySelector<HTMLElement>(".silice-sidebar__areas")!;
  }

  // Las areas de la barra, en su orden: enlaces (una sola pantalla) y botones (abren su panel).
  function areasDeLaBarra(): HTMLElement[] {
    return [...menu().querySelectorAll<HTMLElement>(".silice-barra__item > a, .silice-barra__item > button")];
  }

  // Titulo de cada pantalla de las areas del sidebar (su descripcion accesible es la linea de ayuda).
  function titulosDelSidebar(): string[] {
    return within(areasDelSidebar())
      .getAllByRole("link")
      .map((a) => a.querySelector(".silice-sidebar__titulo")?.textContent ?? "");
  }

  // El selector de obra de la barra (MOD-3b): «Obra: …», «Todas las obras» o, sin obras que ver, «Carpeta: …».
  function botonObra() {
    return within(screen.getByRole("banner")).findByRole("button", { name: /^(Obra: |Todas las obras|Carpeta: )/ });
  }

  // Lo que se ve de cada obra en el panel del selector (su primera linea).
  function obrasDeLaLista(): string[] {
    return within(screen.getByRole("list", { name: "Obras de la carpeta de trabajo" }))
      .getAllByRole("button")
      .map((b) => b.querySelector(".silice-obra__nombre")?.textContent ?? "");
  }

  // «Cambiar carpeta…» al pie del selector abre el dialogo «Carpetas de trabajo».
  async function abrirCarpetas(usuario: ReturnType<typeof userEvent.setup>) {
    await usuario.click(await botonObra());
    await usuario.click(await screen.findByRole("button", { name: "Cambiar carpeta…" }));
    return screen.findByRole("dialog", { name: "Carpetas de trabajo" });
  }

  async function abrirEnElDialogo(usuario: ReturnType<typeof userEvent.setup>, nombre: string) {
    const dialogo = await abrirCarpetas(usuario);
    await usuario.click(await within(dialogo).findByRole("button", { name: `Abrir ${nombre}` }));
  }

  function nombresDeCarpetas(lista: HTMLElement): string[] {
    return within(lista)
      .getAllByRole("listitem")
      .map((li) => li.querySelector(".silice-carpetas__nombre")?.textContent ?? "");
  }

  async function salir(usuario: ReturnType<typeof userEvent.setup>) {
    await usuario.click(await screen.findByRole("button", { name: "Cuenta de Ana Pérez" }));
    await usuario.click(screen.getByRole("button", { name: "Salir" }));
  }

  describe("cabecera", () => {
    test("muestra el nombre de la persona y «Salir», en el menú de la cuenta, llama a alSalir", async () => {
      const usuario = userEvent.setup();
      montar();
      const banner = screen.getByRole("banner");
      expect(await within(banner).findByText("Ana Pérez")).toBeInTheDocument();
      await salir(usuario);
      expect(alSalir).toHaveBeenCalled();
    });

    // Antes en Cabecera.test.tsx: el control de tamaño de letra está en la barra junto a la cuenta.
    test("trae el control de tamaño de letra junto a la cuenta, que lleva el nombre en su nombre accesible y su título", async () => {
      montar();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      const banner = screen.getByRole("banner");
      expect(within(banner).getByRole("group", { name: "Tamaño de letra" })).toBeInTheDocument();
      const cuenta = within(banner).getByRole("button", { name: "Cuenta de Ana Pérez" });
      expect(cuenta).toHaveAttribute("title", "Ana Pérez");
    });

    test("el lado derecho va en orden: obra, recorrido, tamaño de letra y cuenta", async () => {
      const usuario = userEvent.setup();
      montar();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      act(() => iniciarRecorrido(RECORRIDO_AUDITAR));
      onTestFinished(() => terminarRecorrido());
      await usuario.click(within(screen.getByRole("complementary", { name: "Recorrido" })).getByRole("button", { name: "Ocultar" }));
      const banner = screen.getByRole("banner");
      const orden = [
        within(banner).getByRole("button", { name: /^Obra: / }),
        within(banner).getByRole("button", { name: "Recorrido" }),
        within(banner).getByRole("group", { name: "Tamaño de letra" }),
        within(banner).getByRole("button", { name: "Cuenta de Ana Pérez" }),
      ];
      for (let i = 1; i < orden.length; i++) {
        expect(orden[i - 1].compareDocumentPosition(orden[i]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
      }
    });

    test("«Saltar al contenido» es lo primero que se alcanza con Tab y manda el foco a la pagina", async () => {
      const usuario = userEvent.setup();
      montar();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      await usuario.tab();
      const saltar = screen.getByRole("button", { name: "Saltar al contenido" });
      expect(saltar).toHaveFocus();
      await usuario.keyboard("{Enter}");
      expect(screen.getByRole("main")).toHaveFocus();
    });

    test("hay una sola region main y su cabecera dice Sílice", async () => {
      montar();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      expect(screen.getAllByRole("main")).toHaveLength(1);
      expect(screen.getByRole("banner")).toHaveTextContent("Sílice");
    });

    test("la obra se ve en la barra (plan de modulos, MOD-3b: obra en vez de carpeta y proyecto)", async () => {
      montar();
      const banner = screen.getByRole("banner");
      expect(await within(banner).findByRole("button", { name: "Obra: sin elegir. Elegir obra" })).toHaveTextContent("Obra: sin elegir");
      expect(within(banner).queryByRole("button", { name: /^Carpeta de trabajo:/ })).toBeNull();
    });
  });

  describe("barra superior", () => {
    test("muestra las áreas del módulo que la cuenta puede usar, y en cada panel solo sus pantallas permitidas", async () => {
      const usuario = userEvent.setup();
      montar();
      // Sin control_de_obra, a «Control» solo le queda Escenarios: pasa a enlace con el nombre del área.
      expect(areasDeLaBarra().map((a) => a.textContent)).toEqual(["Inicio", "Obras", "Partidas", "Control"]);
      expect(within(menu()).getByRole("link", { name: "Control" })).toHaveAttribute("href", "/escenarios");
      await usuario.click(within(menu()).getByRole("button", { name: "Obras" }));
      const panel = within(menu()).getByRole("region", { name: "Obras" });
      expect(within(panel).getAllByRole("link").map((a) => a.getAttribute("href"))).toEqual(["/tablero", "/hoja"]);
      expect(within(menu()).queryByRole("link", { name: "Control de obra" })).not.toBeInTheDocument();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
    });

    test("junto a «Sílice» la barra dice el módulo abierto, como texto", async () => {
      montar();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      const banner = screen.getByRole("banner");
      const nombre = within(banner).getByText("Presupuestos y obras");
      expect(nombre.closest("a")).toBeNull();
    });

    test.each([
      ["ana", "Inicio de presupuestos y obras", "Presupuestos y obras", ["Inicio", "Obras", "Partidas", "Mercado", "Aprobaciones", "Control"]],
      ["rita", "Inicio de auditoría", "Auditoría", ["Inicio", "Auditar", "Paquetes", "Historial"]],
      ["admin", "Inicio de presupuestos y obras", "Presupuestos y obras", ["Inicio", "Mercado"]],
    ] as const)("%s entra en el inicio de su módulo y ve en la barra las áreas de su rol", async (rol, inicio, modulo, esperadas) => {
      montar(sesionCon({ login: rol, acciones: ACCIONES_POR_ROL[rol] }), "/", LIGERAS);
      await screen.findByRole("heading", { name: inicio });
      expect(within(screen.getByRole("banner")).getByText(modulo)).toBeInTheDocument();
      expect(areasDeLaBarra().map((a) => a.textContent)).toEqual(esperadas);
    });

    // Foco de revision 4, en la barra: oraculo escrito a mano (plan de modulos, MOD-1).
    test.each([
      [
        "ana",
        [
          "/obras",
          "/hoja",
          "/elaborar",
          "/tablero",
          "/entregar",
          "/componer",
          "/catalogo",
          "/similares",
          "/mercado",
          "/actualizacion",
          "/historico",
          "/simulador",
          "/aprobar",
          "/control",
          "/reajuste",
          "/escenarios",
        ],
      ],
      ["rita", ["/auditoria", "/libros", "/revisar", "/historial"]],
      ["admin", ["/obras", "/precios_empresa", "/indices"]],
    ] as const)(
      "con %s cada pantalla de su módulo de entrada sale una sola vez en la barra y en las áreas del sidebar",
      async (rol, esperadas) => {
        const usuario = userEvent.setup();
        montar(sesionCon({ login: rol, acciones: ACCIONES_POR_ROL[rol] }), "/", LIGERAS);
        await screen.findByRole("heading", { level: 1 });
        const vistas: string[] = [];
        for (const area of areasDeLaBarra()) {
          if (area.tagName === "BUTTON") {
            await usuario.click(area);
            const id = area.getAttribute("aria-controls")!;
            vistas.push(...within(document.getElementById(id)!).getAllByRole("link").map((a) => a.getAttribute("href")!));
          } else {
            vistas.push(area.getAttribute("href")!);
          }
        }
        expect(vistas).toEqual(esperadas);
        await abrirModulos(usuario);
        const enCapa = within(areasDelSidebar())
          .getAllByRole("link")
          .map((a) => a.getAttribute("href")!);
        expect(new Set(enCapa).size).toBe(enCapa.length);
        expect([...enCapa].sort()).toEqual([...esperadas].sort());
      },
    );

    test("«Obras» empieza cerrado, se abre con su botón y se vuelve a cerrar", async () => {
      const usuario = userEvent.setup();
      montar();
      const boton = within(menu()).getByRole("button", { name: "Obras" });
      expect(boton).toHaveAttribute("aria-expanded", "false");
      expect(within(menu()).queryByRole("link", { name: "Hoja del proyecto" })).not.toBeInTheDocument();
      await usuario.click(boton);
      expect(boton).toHaveAttribute("aria-expanded", "true");
      expect(within(menu()).getByRole("link", { name: "Hoja del proyecto" })).toBeVisible();
      await usuario.click(boton);
      expect(boton).toHaveAttribute("aria-expanded", "false");
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
    });

    test("estando en una pantalla de un panel, esa área se marca como actual y su panel marca la pantalla", async () => {
      const usuario = userEvent.setup();
      montar(sesionCon(), "/hoja");
      const obras = within(menu()).getByRole("button", { name: "Obras" });
      expect(obras).toHaveClass("silice-barra__area--actual");
      expect(within(menu()).getByRole("link", { name: "Partidas" })).not.toHaveAttribute("aria-current");
      await usuario.click(obras);
      expect(within(menu()).getByRole("link", { name: "Hoja del proyecto" })).toHaveAttribute("aria-current", "page");
      await screen.findByRole("heading", { name: "Otra pantalla" });
    });

    test("cada pantalla del panel lleva su línea de ayuda como descripción", async () => {
      const usuario = userEvent.setup();
      montar();
      await usuario.click(within(menu()).getByRole("button", { name: "Obras" }));
      const enlace = within(menu()).getByRole("link", { name: "Tablero del proyecto" });
      expect(enlace).toHaveAccessibleDescription("Cómo va el proyecto");
      expect(within(menu()).getByText("Cómo va el proyecto")).toBeVisible();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
    });

    test("en modo entrega no aparece ninguna pantalla de Investigación, ni en la barra ni en el sidebar", async () => {
      const usuario = userEvent.setup();
      montar(sesionCon({ modo_entrega: true }));
      // Sin Escenarios, «Control» queda sin pantallas y no se pinta.
      expect(areasDeLaBarra().map((a) => a.textContent)).toEqual(["Inicio", "Obras", "Partidas"]);
      expect(within(menu()).queryByRole("link", { name: "Escenarios de sensibilidad" })).not.toBeInTheDocument();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      await abrirModulos(usuario);
      expect(within(sidebar()).queryByText("Escenarios de sensibilidad")).not.toBeInTheDocument();
    });

    test("en modo entrega, con todas las acciones de ana, ninguna pantalla de Investigación sale en la navegación", async () => {
      const usuario = userEvent.setup();
      montar(sesionCon({ acciones: ACCIONES_POR_ROL.ana, modo_entrega: true }), "/obras", LIGERAS);
      await screen.findByRole("heading", { name: "Inicio de presupuestos y obras" });
      for (const nombre of ["Obras", "Partidas", "Mercado", "Control"]) {
        await usuario.click(within(menu()).getByRole("button", { name: nombre }));
        for (const p of REGISTRO.filter((q) => q.seccion === "Investigación")) {
          expect(within(menu()).queryByRole("link", { name: p.titulo })).not.toBeInTheDocument();
        }
      }
      await usuario.click(document.body);
      await abrirModulos(usuario);
      expect(titulosDelSidebar().length).toBeGreaterThan(0);
      for (const p of REGISTRO.filter((q) => q.seccion === "Investigación")) expect(titulosDelSidebar()).not.toContain(p.titulo);
    });

    test("la pagina actual es un enlace marcado en su panel y su área va marcada como actual", async () => {
      const usuario = userEvent.setup();
      montar();
      const obras = within(menu()).getByRole("button", { name: "Obras" });
      expect(obras).toHaveClass("silice-barra__area--actual");
      await usuario.click(obras);
      const enlace = within(menu()).getByRole("link", { name: "Tablero del proyecto" });
      expect(enlace).toHaveAttribute("href", "/tablero");
      expect(enlace).toHaveAttribute("aria-current", "page");
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
    });

    test("toda pantalla de la navegación es un enlace de esta interfaz: ni «clásica» ni enlaces fuera de ella", async () => {
      const usuario = userEvent.setup();
      montar();
      await usuario.click(within(menu()).getByRole("button", { name: "Obras" }));
      await abrirModulos(usuario);
      for (const nav of [menu(), sidebar()]) {
        expect(nav).not.toHaveTextContent(/clásica/i);
        expect(nav.querySelector("[class*='silice-menu__']")).toBeNull();
        expect(nav.querySelector("a[target=_blank]")).toBeNull();
        expect(nav.querySelector("[aria-disabled]")).toBeNull();
      }
      expect(within(menu()).getByRole("link", { name: "Partidas" })).toHaveAttribute("href", "/catalogo");
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
    });

    test("se recorre con el teclado: Tab llega al área, Enter abre su panel, las flechas recorren y Enter cambia de página", async () => {
      const usuario = userEvent.setup();
      montar();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      const obras = within(menu()).getByRole("button", { name: "Obras" });
      for (let i = 0; i < 40 && document.activeElement !== obras; i++) await usuario.tab();
      expect(obras).toHaveFocus();
      await usuario.keyboard("{Enter}");
      expect(obras).toHaveAttribute("aria-expanded", "true");
      // En el registro de prueba el tablero va antes que la hoja.
      const tablero = within(menu()).getByRole("link", { name: "Tablero del proyecto" });
      expect(tablero).toHaveFocus();
      await usuario.keyboard("{ArrowDown}");
      const hoja = within(menu()).getByRole("link", { name: "Hoja del proyecto" });
      expect(hoja).toHaveFocus();
      await usuario.keyboard("{ArrowUp}");
      expect(tablero).toHaveFocus();
      await usuario.keyboard("{ArrowDown}{Enter}");
      const titulo = await screen.findByRole("heading", { name: "Otra pantalla" });
      await waitFor(() => expect(titulo).toHaveFocus());
    });

    test("los rótulos de área no son encabezados, ni en la barra ni en el sidebar (el h1 de la página es el primero que se lee)", async () => {
      const usuario = userEvent.setup();
      montar();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      await usuario.click(within(menu()).getByRole("button", { name: "Obras" }));
      expect(within(menu()).queryAllByRole("heading")).toHaveLength(0);
      await abrirModulos(usuario);
      expect(within(sidebar()).queryAllByRole("heading")).toHaveLength(0);
      expect(sidebar().querySelectorAll(".silice-sidebar__rotulo-area").length).toBeGreaterThan(0);
    });
  });

  // Plan de modulos (MOD-1): la direccion de entrada, el modulo actual y el ultimo modulo recordado por cuenta.
  describe("modulos: entrada, modulo actual y preferencia", () => {
    const PUT = "/v1/sesion/preferencias";

    function llamadasPut() {
      return fetchFalso.mock.calls.filter((c) => String(c[0]) === PUT && c[1]?.method === "PUT");
    }

    function sesionDe(rol: "ana" | "rita" | "admin", modulo: ModuloId | null) {
      return sesionCon({ login: rol, acciones: ACCIONES_POR_ROL[rol], preferencias: { modulo, sidebar_fijado: false } });
    }

    // Para navegar sin la barra (la direccion escrita a mano o un marcador).
    const historia: { ir: NavigateFunction | null } = { ir: null };
    function Navegador() {
      const ir = useNavigate();
      useEffect(() => {
        historia.ir = ir;
      }, [ir]);
      return null;
    }

    function montarCon(sesion: SesionRespuesta, ruta: string) {
      return render(
        <MemoryRouter initialEntries={[ruta]}>
          <Shell sesion={sesion} alSalir={alSalir} alExpirar={alExpirar} paginas={LIGERAS} />
          <Navegador />
        </MemoryRouter>,
      );
    }

    test.each(["/", "/inicio", "/no-existe"])("%s con «obras» guardado lleva al inicio de Presupuestos y obras", async (ruta) => {
      montarCon(sesionDe("ana", "obras"), ruta);
      expect(await screen.findByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" })).toBeInTheDocument();
    });

    test("ana con «auditoria» guardado entra en Auditoría", async () => {
      montarCon(sesionDe("ana", "auditoria"), "/");
      expect(await screen.findByRole("heading", { level: 1, name: "Inicio de auditoría" })).toBeInTheDocument();
    });

    test("rita con «produccion» guardado (que no puede usar) entra en Auditoría", async () => {
      montarCon(sesionDe("rita", "produccion"), "/inicio");
      expect(await screen.findByRole("heading", { level: 1, name: "Inicio de auditoría" })).toBeInTheDocument();
    });

    test("sin módulo guardado, quien arma entra en Presupuestos y obras y quien revisa en Auditoría", async () => {
      const { unmount } = montarCon(sesionDe("ana", null), "/");
      expect(await screen.findByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" })).toBeInTheDocument();
      unmount();
      montarCon(sesionDe("rita", null), "/");
      expect(await screen.findByRole("heading", { level: 1, name: "Inicio de auditoría" })).toBeInTheDocument();
    });

    test("una API anterior sin preferencias entra por el rol", async () => {
      montarCon(sesionCon({ acciones: ACCIONES_POR_ROL.admin }), "/");
      expect(await screen.findByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" })).toBeInTheDocument();
    });

    test("una cuenta sin ningún módulo visible entra en la primera pantalla de fuera de los módulos", async () => {
      montarCon(sesionCon({ acciones: ["administrar_cuentas"] }), "/");
      expect(await screen.findByRole("heading", { level: 1, name: "Administración" })).toBeInTheDocument();
      expect(screen.queryByText("Presupuestos y obras")).not.toBeInTheDocument();
    });

    test("ir de /libros a /hoja guarda «obras» una sola vez; ir a /acerca no guarda nada", async () => {
      montarCon(sesionDe("ana", "auditoria"), "/libros");
      await screen.findByRole("heading", { level: 1, name: "Libro de la empresa" });
      expect(llamadasPut()).toHaveLength(0);
      act(() => void historia.ir!("/hoja"));
      await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
      await waitFor(() => expect(llamadasPut()).toHaveLength(1));
      const [, init] = llamadasPut()[0];
      expect(init?.body).toBe(JSON.stringify({ modulo: "obras" }));
      expect(new Headers(init?.headers).get("X-Silice-CSRF")).toBe("tok");
      act(() => void historia.ir!("/elaborar"));
      await screen.findByRole("heading", { level: 1, name: "Elaborar un presupuesto" });
      act(() => void historia.ir!("/acerca"));
      await screen.findByRole("heading", { level: 1, name: "Acerca de Sílice" });
      await new Promise((r) => setTimeout(r, 30));
      expect(llamadasPut()).toHaveLength(1);
    });

    test("foco 1: un marcador a /componer con «auditoria» guardado abre Presupuestos y obras y lo recuerda", async () => {
      const { container } = montarCon(sesionDe("ana", "auditoria"), "/componer");
      await screen.findByRole("heading", { level: 1, name: "Componer una partida" });
      expect(within(screen.getByRole("banner")).getByText("Presupuestos y obras")).toBeInTheDocument();
      expect(container.querySelector(".silice-marco")).toHaveAttribute("data-modulo", "obras");
      await waitFor(() => expect(llamadasPut()).toHaveLength(1));
      expect(llamadasPut()[0][1]?.body).toBe(JSON.stringify({ modulo: "obras" }));
    });

    test("foco 1: Administración queda en el último módulo usado (la barra y data-modulo no cambian)", async () => {
      const { container } = montarCon(sesionDe("admin", "produccion"), "/existencias");
      await screen.findByRole("heading", { level: 1, name: "Existencias de la arenera" });
      act(() => void historia.ir!("/administracion"));
      await screen.findByRole("heading", { level: 1, name: "Administración" });
      expect(within(screen.getByRole("banner")).getByText("Producción")).toBeInTheDocument();
      expect(container.querySelector(".silice-marco")).toHaveAttribute("data-modulo", "produccion");
      expect(areasDeLaBarra().map((a) => a.textContent)).toEqual(["Inicio", "Existencias"]);
      expect(llamadasPut()).toHaveLength(0);
    });

    test("entrar directo a Acerca sin módulo guardado muestra el módulo de entrada y no guarda nada", async () => {
      const { container } = montarCon(sesionDe("rita", null), "/acerca");
      await screen.findByRole("heading", { level: 1, name: "Acerca de Sílice" });
      expect(container.querySelector(".silice-marco")).toHaveAttribute("data-modulo", "auditoria");
      await new Promise((r) => setTimeout(r, 30));
      expect(llamadasPut()).toHaveLength(0);
    });

    test("una pantalla de un módulo que la cuenta no puede usar no cambia el módulo ni lo guarda", async () => {
      const { container } = montarCon(sesionDe("rita", "auditoria"), "/existencias");
      expect(await screen.findByText("Su cuenta no tiene permiso para esta pantalla o acción.")).toBeInTheDocument();
      expect(container.querySelector(".silice-marco")).toHaveAttribute("data-modulo", "auditoria");
      await new Promise((r) => setTimeout(r, 30));
      expect(llamadasPut()).toHaveLength(0);
    });

    test("un 401 al guardar el módulo da la sesión por vencida", async () => {
      const base = fetchFalso.getMockImplementation()!;
      fetchFalso.mockImplementation(async (entrada, init) =>
        String(entrada) === PUT ? json({ detalle: "Sin sesión." }, 401) : base(entrada, init),
      );
      montarCon(sesionDe("ana", "auditoria"), "/hoja");
      await waitFor(() => expect(alExpirar).toHaveBeenCalled());
    });

    test("otro error al guardar el módulo no molesta a la persona", async () => {
      const base = fetchFalso.getMockImplementation()!;
      fetchFalso.mockImplementation(async (entrada, init) =>
        String(entrada) === PUT ? json({ detalle: "La base de la instalación no responde." }, 500) : base(entrada, init),
      );
      montarCon(sesionDe("ana", "auditoria"), "/hoja");
      await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
      await waitFor(() => expect(llamadasPut()).toHaveLength(1));
      await new Promise((r) => setTimeout(r, 30));
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(alExpirar).not.toHaveBeenCalled();
    });

    test("el módulo llega a las páginas por el contexto", async () => {
      function VeModulo() {
        const { modulo } = useAplicacion();
        return <h1>{`modulo=${modulo ?? "ninguno"}`}</h1>;
      }
      const paginas = LIGERAS.map((p) => (p.id === "historial" ? { ...p, cargar: async () => ({ default: VeModulo }) } : p));
      render(
        <MemoryRouter initialEntries={["/historial"]}>
          <Shell sesion={sesionDe("ana", "obras")} alSalir={alSalir} alExpirar={alExpirar} paginas={paginas} />
        </MemoryRouter>,
      );
      expect(await screen.findByRole("heading", { name: "modulo=auditoria" })).toBeInTheDocument();
    });
  });

  describe("recorrido guiado", () => {
    test("el recorrido en curso aparece en su columna junto al contenido y se cierra desde ahí", async () => {
      const usuario = userEvent.setup();
      montar();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      expect(screen.queryByRole("complementary", { name: "Recorrido" })).not.toBeInTheDocument();
      act(() => iniciarRecorrido(RECORRIDO_AUDITAR));
      onTestFinished(() => terminarRecorrido());
      const columna = screen.getByRole("complementary", { name: "Recorrido" });
      expect(within(columna).getByText(RECORRIDO_AUDITAR.titulo)).toBeInTheDocument();
      await usuario.click(within(columna).getByRole("button", { name: "Terminar recorrido" }));
      expect(screen.queryByRole("complementary", { name: "Recorrido" })).not.toBeInTheDocument();
      expect(recorridoEnCurso()).toBeNull();
    });

    test("con la columna a la vista el contenido cede su ancho (clase silice-con-recorrido); oculta o sin recorrido, no", async () => {
      const usuario = userEvent.setup();
      const { container } = montar();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      expect(container.querySelector(".silice-con-recorrido .silice-contenido")).toBeNull();
      act(() => iniciarRecorrido(RECORRIDO_AUDITAR));
      onTestFinished(() => terminarRecorrido());
      expect(container.querySelector(".silice-con-recorrido .silice-contenido")).not.toBeNull();
      await usuario.click(screen.getByRole("button", { name: "Ocultar" }));
      expect(container.querySelector(".silice-con-recorrido")).toBeNull();
      await usuario.click(within(screen.getByRole("banner")).getByRole("button", { name: "Recorrido" }));
      expect(screen.getByRole("complementary", { name: "Recorrido" })).toBeInTheDocument();
      expect(container.querySelector(".silice-con-recorrido .silice-contenido")).not.toBeNull();
    });

    test("la columna no se cierra al navegar", async () => {
      const usuario = userEvent.setup();
      montar();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      act(() => iniciarRecorrido(RECORRIDO_AUDITAR));
      onTestFinished(() => terminarRecorrido());
      await usuario.click(within(menu()).getByRole("link", { name: "Partidas" }));
      await screen.findByRole("heading", { name: "Otra pantalla" });
      expect(screen.getByRole("complementary", { name: "Recorrido" })).toBeInTheDocument();
    });

    // Foco de revision 4 del plan: Esc cierra el panel del area, no el recorrido.
    test("con un recorrido activo y el panel de «Obras» abierto, Esc cierra solo el panel", async () => {
      const usuario = userEvent.setup();
      montar();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      act(() => iniciarRecorrido(RECORRIDO_AUDITAR));
      onTestFinished(() => terminarRecorrido());
      const obras = within(menu()).getByRole("button", { name: "Obras" });
      await usuario.click(obras);
      expect(obras).toHaveAttribute("aria-expanded", "true");
      await usuario.keyboard("{Escape}");
      expect(obras).toHaveAttribute("aria-expanded", "false");
      expect(within(menu()).queryByRole("region", { name: "Obras" })).not.toBeInTheDocument();
      expect(screen.getByRole("complementary", { name: "Recorrido" })).toBeInTheDocument();
      expect(recorridoEnCurso()).not.toBeNull();
    });
  });

  describe("fin de sesion y recorrido", () => {
    test("Salir cierra el recorrido en curso", async () => {
      const usuario = userEvent.setup();
      montar();
      act(() => iniciarRecorrido(RECORRIDO_AUDITAR));
      onTestFinished(() => terminarRecorrido());
      expect(screen.getByRole("complementary", { name: "Recorrido" })).toBeInTheDocument();
      await salir(usuario);
      expect(alSalir).toHaveBeenCalled();
      expect(screen.queryByRole("complementary", { name: "Recorrido" })).not.toBeInTheDocument();
      expect(recorridoEnCurso()).toBeNull();
    });

    test("una sesion vencida (401) cierra el recorrido en curso", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockImplementation(async (entrada, init) => {
        const ruta = String(entrada);
        if (ruta === "/v1/casos" && (init?.method ?? "GET") === "GET") return json(CASOS);
        if (ruta === "/v1/casos/actual") return json({ detalle: "Sin sesión." }, 401);
        if (ruta === "/v1/proyectos") return json(PROYECTOS);
        return json({ detalle: "No encontrado." }, 404);
      });
      montar();
      act(() => iniciarRecorrido(RECORRIDO_AUDITAR));
      onTestFinished(() => terminarRecorrido());
      await abrirEnElDialogo(usuario, "arenaza");
      await waitFor(() => expect(alExpirar).toHaveBeenCalled());
      expect(recorridoEnCurso()).toBeNull();
    });
  });

  test("la cabecera no reserva una ranura vacía: ninguna página pinta ya controles allí (T8)", async () => {
    const { container } = render(
      <MemoryRouter initialEntries={["/tablero"]}>
        <Shell sesion={sesionCon()} alSalir={alSalir} alExpirar={alExpirar} paginas={PAGINAS} />
      </MemoryRouter>,
    );
    await screen.findByRole("heading", { name: "Pantalla del tablero" });
    expect(container.querySelector(".silice-cabecera__libro")).toBeNull();
  });

  describe("rutas", () => {
    test("carga la pagina de la ruta cuando se abre, no antes", async () => {
      const cargar = vi.fn(async () => ({ default: PaginaA }));
      const paginas: PaginaDef[] = [{ ...PAGINAS[0], cargar }, ...PAGINAS.slice(1)];
      render(
        <MemoryRouter initialEntries={["/acerca"]}>
          <Shell sesion={sesionCon()} alSalir={alSalir} alExpirar={alExpirar} paginas={paginas} />
        </MemoryRouter>,
      );
      expect(await screen.findByRole("heading", { name: "Otra pantalla" })).toBeInTheDocument();
      expect(cargar).not.toHaveBeenCalled();
      expect(screen.queryByText(/clásica/i)).toBeNull();
    });

    test("mientras llega la pagina muestra un esqueleto anunciado", async () => {
      const paginas: PaginaDef[] = [{ ...PAGINAS[0], cargar: () => new Promise(() => {}) }, ...PAGINAS.slice(1)];
      render(
        <MemoryRouter initialEntries={["/tablero"]}>
          <Shell sesion={sesionCon()} alSalir={alSalir} alExpirar={alExpirar} paginas={paginas} />
        </MemoryRouter>,
      );
      expect(await screen.findByRole("status", { name: "Cargando la pantalla" })).toBeInTheDocument();
    });

    test("la raiz lleva al inicio del módulo de entrada (quien arma: Presupuestos y obras)", async () => {
      montar(sesionCon(), "/");
      expect(await screen.findByRole("heading", { name: "Inicio de presupuestos y obras" })).toBeInTheDocument();
    });

    test("una ruta desconocida redirige igual que la raíz", async () => {
      montar(sesionCon(), "/no-existe");
      expect(await screen.findByRole("heading", { name: "Inicio de presupuestos y obras" })).toBeInTheDocument();
    });

    test("una ruta que la cuenta no puede usar dice que no tiene permiso, aunque se escriba la direccion", async () => {
      montar(sesionCon(), "/control");
      expect(await screen.findByText("Su cuenta no tiene permiso para esta pantalla o acción.")).toBeInTheDocument();
    });

    test("en modo entrega la ruta de Investigacion tampoco entra", async () => {
      montar(sesionCon({ modo_entrega: true }), "/escenarios");
      expect(await screen.findByText("Su cuenta no tiene permiso para esta pantalla o acción.")).toBeInTheDocument();
    });

    test("si la pagina no se puede cargar muestra el error en vez de dejar la pantalla en blanco", async () => {
      const paginas: PaginaDef[] = [
        { ...PAGINAS[0], cargar: () => Promise.reject(new Error("chunk")) },
        ...PAGINAS.slice(1),
      ];
      vi.spyOn(console, "error").mockImplementation(() => {});
      render(
        <MemoryRouter initialEntries={["/tablero"]}>
          <Shell sesion={sesionCon()} alSalir={alSalir} alExpirar={alExpirar} paginas={paginas} />
        </MemoryRouter>,
      );
      expect(await alertaConTexto()).toHaveTextContent("No se pudo abrir la pantalla");
      vi.restoreAllMocks();
    });
  });

  // Plan de modulos, MOD-3b: la carpeta se cambia en el dialogo «Carpetas de trabajo» (pie del selector de obra,
  // «Cambiar carpeta…»); el aviso ya no dice que vuelve a la de por defecto al reiniciar (MOD-0 la recuerda por cuenta).
  describe("cambiar de carpeta", () => {
    test("el diálogo lista las carpetas y marca la abierta", async () => {
      const usuario = userEvent.setup();
      montar();
      const dialogo = await abrirCarpetas(usuario);
      const lista = await within(dialogo).findByRole("list", { name: "Carpetas de trabajo de la instalación" });
      expect(nombresDeCarpetas(lista)).toEqual(["clinica", "arenaza"]);
      expect(within(lista).getAllByRole("listitem")[0]).toHaveAttribute("aria-current", "true");
    });

    test("abrir otra hace POST /v1/casos/actual con el token y avisa que ahora trabaja con ella", async () => {
      const usuario = userEvent.setup();
      montar();
      await abrirEnElDialogo(usuario, "arenaza");
      await waitFor(() => expect(fetchFalso.mock.calls.some((c) => String(c[0]) === "/v1/casos/actual")).toBe(true));
      const llamada = fetchFalso.mock.calls.find((c) => String(c[0]) === "/v1/casos/actual");
      expect(llamada?.[1]?.method).toBe("POST");
      expect(llamada?.[1]?.body).toBe(JSON.stringify({ nombre: "arenaza" }));
      expect(new Headers(llamada?.[1]?.headers).get("X-Silice-CSRF")).toBe("tok");
      const aviso = (await screen.findByText("Ahora trabaja con la carpeta de trabajo «arenaza».")).closest(".cds--inline-notification");
      expect(aviso).not.toBeNull();
      const dentro = within(aviso as HTMLElement);
      expect(dentro.getByText("Carpeta de trabajo cambiada")).toBeInTheDocument();
      expect(dentro.queryByText(/\bcaso\b/i)).toBeNull();
      expect(dentro.queryByText(/reinici/i)).toBeNull();
      // El pie del selector dice la carpeta nueva.
      await usuario.click(await botonObra());
      expect(await screen.findByText("Carpeta: arenaza")).toBeInTheDocument();
    });

    test("el aviso y la lista muestran la carpeta sin la extension .db", async () => {
      const usuario = userEvent.setup();
      const con = { nombre: "clinica.db", ruta_relativa: "data/clinica.db" };
      const otra = { nombre: "obra.db", ruta_relativa: "data/obra.db" };
      let actual = con;
      fetchFalso.mockImplementation(async (entrada, init) => {
        const ruta = String(entrada);
        if (ruta === "/v1/casos" && (init?.method ?? "GET") === "GET") return json({ actual, casos: [con, otra] });
        if (ruta === "/v1/casos/actual") {
          actual = otra;
          return json(otra);
        }
        if (ruta === "/v1/proyectos") return json(PROYECTOS);
        return json({ detalle: "No encontrado." }, 404);
      });
      montar();
      const dialogo = await abrirCarpetas(usuario);
      expect(nombresDeCarpetas(await within(dialogo).findByRole("list", { name: "Carpetas de trabajo de la instalación" }))).toEqual([
        "clinica",
        "obra",
      ]);
      await usuario.click(within(dialogo).getByRole("button", { name: "Abrir obra" }));
      expect(await screen.findByText("Ahora trabaja con la carpeta de trabajo «obra».")).toBeInTheDocument();
    });

    // D1 del recorrido funcional: la carpeta de la sesion se ve aunque no venga en la lista, y elegir otra la cambia.
    test("si la carpeta abierta no está en la lista, el diálogo la muestra como abierta y elegir otra la cambia", async () => {
      const usuario = userEvent.setup();
      const silice = { nombre: "silice.db", ruta_relativa: "data/silice.db" };
      const demo = { nombre: "demo.db", ruta_relativa: "data/demo.db" };
      let actual = silice;
      fetchFalso.mockImplementation(async (entrada, init) => {
        const ruta = String(entrada);
        if (ruta === "/v1/casos" && (init?.method ?? "GET") === "GET") return json({ actual, casos: [demo] });
        if (ruta === "/v1/casos/actual") {
          actual = demo;
          return json(demo);
        }
        if (ruta === "/v1/proyectos") return json(PROYECTOS);
        return json({ detalle: "No encontrado." }, 404);
      });
      montar();
      const dialogo = await abrirCarpetas(usuario);
      const lista = await within(dialogo).findByRole("list", { name: "Carpetas de trabajo de la instalación" });
      expect(nombresDeCarpetas(lista)).toEqual(["silice", "demo"]);
      expect(within(lista).getAllByRole("listitem")[0]).toHaveAttribute("aria-current", "true");
      await usuario.click(within(lista).getByRole("button", { name: "Abrir demo" }));
      await waitFor(() => {
        const llamada = fetchFalso.mock.calls.find((c) => String(c[0]) === "/v1/casos/actual");
        expect(llamada?.[1]?.body).toBe(JSON.stringify({ nombre: "demo.db" }));
      });
      await usuario.click(await botonObra());
      expect(await screen.findByText("Carpeta: demo")).toBeInTheDocument();
    });

    // D6 del recorrido funcional: el aviso no se queda en todas las pantallas.
    test("el aviso de carpeta cambiada se cierra al navegar a otra pantalla", async () => {
      const usuario = userEvent.setup();
      montar();
      await abrirEnElDialogo(usuario, "arenaza");
      expect(await screen.findByText("Carpeta de trabajo cambiada")).toBeInTheDocument();
      await usuario.click(within(menu()).getByRole("link", { name: "Partidas" }));
      await screen.findByRole("heading", { name: "Otra pantalla" });
      expect(screen.queryByText("Carpeta de trabajo cambiada")).not.toBeInTheDocument();
    });

    test("al cambiar de carpeta la pagina se vuelve a montar con la carpeta nueva", async () => {
      const usuario = userEvent.setup();
      montar();
      expect(await screen.findByText("caso=clinica")).toBeInTheDocument();
      await abrirEnElDialogo(usuario, "arenaza");
      expect(await screen.findByText("caso=arenaza")).toBeInTheDocument();
    });

    test("sin la accion cambiar_caso el selector no ofrece «Cambiar carpeta…»", async () => {
      const usuario = userEvent.setup();
      montar(sesionCon({ acciones: ["leer_proyecto"] }));
      await usuario.click(await botonObra());
      expect(await screen.findByText("Carpeta: clinica")).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Cambiar carpeta…" })).not.toBeInTheDocument();
    });

    test("si la API rechaza el cambio muestra el detalle y deja la carpeta anterior", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockImplementation(async (entrada, init) => {
        const ruta = String(entrada);
        if (ruta === "/v1/casos" && (init?.method ?? "GET") === "GET") return json(CASOS);
        if (ruta === "/v1/casos/actual") return json({ detalle: "La carpeta de trabajo ya no existe." }, 404);
        if (ruta === "/v1/proyectos") return json(PROYECTOS);
        return json({ detalle: "No encontrado." }, 404);
      });
      montar();
      await abrirEnElDialogo(usuario, "arenaza");
      expect(await alertaConTexto()).toHaveTextContent("La carpeta de trabajo ya no existe.");
      expect(screen.getByText("caso=clinica")).toBeInTheDocument();
    });

    test("un 401 al cambiar de carpeta avisa que la sesion vencio", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockImplementation(async (entrada, init) => {
        const ruta = String(entrada);
        if (ruta === "/v1/casos" && (init?.method ?? "GET") === "GET") return json(CASOS);
        if (ruta === "/v1/casos/actual") return json({ detalle: "Sin sesión." }, 401);
        if (ruta === "/v1/proyectos") return json(PROYECTOS);
        return json({ detalle: "No encontrado." }, 404);
      });
      montar();
      await abrirEnElDialogo(usuario, "arenaza");
      await waitFor(() => expect(alExpirar).toHaveBeenCalled());
    });
  });
  // Plan de modulos, MOD-2: el sidebar de modulos (estado 3), el boton «Sílice», Esc, fijar/ocultar y la confirmacion al
  // salir. Oraculos escritos a mano (titulos y rutas del registro, acciones por rol de seguridad/permisos.py).
  describe("sidebar de módulos", () => {
    const VARIABLE = "--silice-fijado-posible";
    const PUT = "/v1/sesion/preferencias";
    const historia: { ir: NavigateFunction | null } = { ir: null };
    function Navegador() {
      const ir = useNavigate();
      useEffect(() => {
        historia.ir = ir;
      }, [ir]);
      return null;
    }

    function cuerposPut(): string[] {
      return fetchFalso.mock.calls.filter((c) => String(c[0]) === PUT && c[1]?.method === "PUT").map((c) => String(c[1]?.body));
    }

    function sesionDe(rol: "ana" | "rita" | "admin", modulo: ModuloId | null = null, sidebar_fijado = false) {
      return sesionCon({ login: rol, acciones: ACCIONES_POR_ROL[rol], preferencias: { modulo, sidebar_fijado } });
    }

    function montarCon(sesion: SesionRespuesta, ruta: string, paginas: readonly PaginaDef[] = LIGERAS) {
      return render(
        <MemoryRouter initialEntries={[ruta]}>
          <Shell sesion={sesion} alSalir={alSalir} alExpirar={alExpirar} paginas={paginas} />
          <Navegador />
        </MemoryRouter>,
      );
    }

    // «Componer una partida» con un formulario a medio llenar (foco 3) y la Hoja con un campo de la pagina (foco 2).
    function ComponerSucio() {
      useFormularioSucio("componer", true);
      return <h1>Componer una partida</h1>;
    }
    function HojaConCampo() {
      return (
        <>
          <h1>Hoja del proyecto</h1>
          <input aria-label="Cantidad" />
        </>
      );
    }
    const CON_PAGINAS_PROPIAS = LIGERAS.map((p) =>
      p.id === "componer"
        ? { ...p, cargar: async () => ({ default: ComponerSucio }) }
        : p.id === "hoja"
          ? { ...p, cargar: async () => ({ default: HojaConCampo }) }
          : p,
    );

    const silice = () => screen.getByRole("button", { name: /^Sílice, / });
    const fijado = () => screen.queryByRole("navigation", { name: "Módulos" });
    const enCapa = () => screen.queryByRole("dialog", { name: "Módulos de Sílice" });

    afterEach(() => {
      document.documentElement.style.removeProperty(VARIABLE);
      cancelarSalida();
      olvidarFormularios();
      historia.ir = null;
    });

    test("oculto al empezar; «Sílice» lo abre en capa con el foco en el módulo actual, y lo vuelve a cerrar", async () => {
      const u = userEvent.setup();
      montarCon(sesionDe("ana", "obras"), "/hoja");
      await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
      expect(enCapa()).toBeNull();
      expect(fijado()).toBeNull();
      const boton = screen.getByRole("button", { name: "Sílice, abrir los módulos" });
      expect(boton).toHaveAttribute("aria-expanded", "false");
      await u.click(boton);
      expect(enCapa()).toBeInTheDocument();
      expect(boton).toHaveAttribute("aria-expanded", "true");
      expect(boton).toHaveAccessibleName("Sílice, cerrar los módulos");
      expect(boton).toHaveAttribute("aria-controls", enCapa()!.id);
      const actual = within(enCapa()!).getByRole("link", { name: "Presupuestos y obras" });
      expect(actual).toHaveAttribute("aria-current", "page");
      await waitFor(() => expect(actual).toHaveFocus());
      await u.click(boton);
      expect(enCapa()).toBeNull();
      expect(boton).toHaveAttribute("aria-expanded", "false");
    });

    test("foco 2: con el foco en <main> Esc lo abre; otro Esc lo cierra y el foco vuelve a «Sílice»", async () => {
      const u = userEvent.setup();
      montarCon(sesionDe("ana", "obras"), "/hoja");
      await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
      screen.getByRole("main").focus();
      await u.keyboard("{Escape}");
      expect(enCapa()).toBeInTheDocument();
      await waitFor(() => expect(within(enCapa()!).getByRole("link", { name: "Presupuestos y obras" })).toHaveFocus());
      await u.keyboard("{Escape}");
      expect(enCapa()).toBeNull();
      await waitFor(() => expect(silice()).toHaveFocus());
      expect(silice()).toHaveAccessibleName("Sílice, abrir los módulos");
    });

    test("foco 2: con el foco en un campo de la página, Esc no lo abre y el campo conserva el foco", async () => {
      const u = userEvent.setup();
      montarCon(sesionDe("ana", "obras"), "/hoja", CON_PAGINAS_PROPIAS);
      const campo = await screen.findByRole("textbox", { name: "Cantidad" });
      await u.click(campo);
      await u.keyboard("{Escape}");
      expect(enCapa()).toBeNull();
      expect(campo).toHaveFocus();
    });

    test("foco 2: con el panel de «Obras» abierto, el primer Esc cierra solo el panel; el segundo abre el sidebar", async () => {
      const u = userEvent.setup();
      montarCon(sesionDe("ana", "obras"), "/hoja");
      await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
      const obras = within(menu()).getByRole("button", { name: "Obras" });
      await u.click(obras);
      expect(obras).toHaveAttribute("aria-expanded", "true");
      await u.keyboard("{Escape}");
      expect(obras).toHaveAttribute("aria-expanded", "false");
      expect(obras).toHaveFocus();
      expect(enCapa()).toBeNull();
      await u.keyboard("{Escape}");
      expect(enCapa()).toBeInTheDocument();
    });

    test("foco 2: con el menú de la cuenta abierto, Esc lo cierra a él y no abre el sidebar", async () => {
      const u = userEvent.setup();
      montarCon(sesionDe("ana", "obras"), "/hoja");
      await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
      const cuenta = screen.getByRole("button", { name: "Cuenta de Ana Pérez" });
      await u.click(cuenta);
      expect(cuenta).toHaveAttribute("aria-expanded", "true");
      await u.keyboard("{Escape}");
      expect(cuenta).toHaveAttribute("aria-expanded", "false");
      expect(enCapa()).toBeNull();
    });

    test("foco 2: con un recorrido activo, abrir y cerrar el sidebar con Esc no termina el recorrido", async () => {
      const u = userEvent.setup();
      montarCon(sesionDe("ana", "obras"), "/hoja");
      await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
      act(() => iniciarRecorrido(RECORRIDO_AUDITAR));
      onTestFinished(() => terminarRecorrido());
      screen.getByRole("main").focus();
      await u.keyboard("{Escape}");
      expect(enCapa()).toBeInTheDocument();
      await u.keyboard("{Escape}");
      expect(enCapa()).toBeNull();
      expect(recorridoEnCurso()).not.toBeNull();
      expect(screen.getByRole("complementary", { name: "Recorrido" })).toBeInTheDocument();
    });

    test("foco atrapado en la capa: Tab desde el último vuelve al primero y Mayús+Tab desde el primero va al último", async () => {
      const u = userEvent.setup();
      montarCon(sesionDe("ana", "obras"), "/hoja");
      await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
      await u.click(silice());
      // Sin ancho para fijarlo no hay «Fijar»: lo último es «Acerca de Sílice», al pie.
      const primero = within(enCapa()!).getByRole("link", { name: "Auditoría" });
      const ultimo = within(enCapa()!).getByRole("link", { name: "Acerca de Sílice" });
      ultimo.focus();
      await u.tab();
      expect(primero).toHaveFocus();
      await u.tab({ shift: true });
      expect(ultimo).toHaveFocus();
    });

    test("clic en la capa lo cierra y devuelve el foco a «Sílice»", async () => {
      const u = userEvent.setup();
      const { container } = montarCon(sesionDe("ana", "obras"), "/hoja");
      await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
      await u.click(silice());
      await u.click(container.querySelector<HTMLElement>(".silice-sidebar__fondo")!);
      expect(enCapa()).toBeNull();
      await waitFor(() => expect(silice()).toHaveFocus());
    });

    test("elegir «Auditoría» navega a su inicio, cierra el sidebar, el foco va al h1 y se recuerda el módulo", async () => {
      const u = userEvent.setup();
      montarCon(sesionDe("ana", "obras"), "/hoja");
      await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
      await u.click(silice());
      await u.click(within(enCapa()!).getByRole("link", { name: "Auditoría" }));
      const titulo = await screen.findByRole("heading", { level: 1, name: "Inicio de auditoría" });
      expect(enCapa()).toBeNull();
      await waitFor(() => expect(titulo).toHaveFocus());
      expect(within(screen.getByRole("banner")).getByText("Auditoría")).toBeInTheDocument();
      await waitFor(() => expect(cuerposPut()).toEqual(['{"modulo":"auditoria"}']));
    });

    test("«Fijar» lo deja como franja que empuja (navegación «Módulos») y lo recuerda; «Ocultar» lo devuelve oculto", async () => {
      const u = userEvent.setup();
      document.documentElement.style.setProperty(VARIABLE, "1");
      const { container } = montarCon(sesionDe("ana", "obras"), "/hoja");
      await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
      await u.click(silice());
      await u.click(within(enCapa()!).getByRole("button", { name: "Fijar" }));
      await waitFor(() => expect(cuerposPut()).toEqual(['{"sidebar_fijado":true}']));
      expect(container.querySelector(".silice-marco")).toHaveClass("silice-marco--fijado");
      expect(enCapa()).toBeNull();
      expect(container.querySelector(".silice-sidebar__fondo")).toBeNull();
      const nav = fijado()!;
      expect(nav).toBeInTheDocument();
      expect(silice()).toHaveAccessibleName("Sílice, ir a los módulos");
      expect(silice()).toHaveAttribute("aria-expanded", "true");
      const ocultar = within(nav).getByRole("button", { name: "Ocultar" });
      await waitFor(() => expect(ocultar).toHaveFocus());
      await u.click(ocultar);
      await waitFor(() => expect(cuerposPut()).toEqual(['{"sidebar_fijado":true}', '{"sidebar_fijado":false}']));
      expect(fijado()).toBeNull();
      expect(container.querySelector(".silice-marco")).not.toHaveClass("silice-marco--fijado");
      await waitFor(() => expect(silice()).toHaveFocus());
    });

    test("abierto en capa con fijado sin ancho: al ensancharse pasa a franja y al estrecharse no vuelve la capa sola", async () => {
      const u = userEvent.setup();
      document.documentElement.style.setProperty(VARIABLE, "0");
      montarCon(sesionDe("ana", "obras", true), "/hoja");
      await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
      await u.click(silice());
      expect(enCapa()).toBeInTheDocument();
      act(() => {
        document.documentElement.style.setProperty(VARIABLE, "1");
        window.dispatchEvent(new Event("resize"));
      });
      expect(enCapa()).toBeNull();
      expect(fijado()).toBeInTheDocument();
      const titulo = screen.getByRole("heading", { level: 1, name: "Hoja del proyecto" });
      titulo.tabIndex = -1;
      titulo.focus();
      act(() => {
        document.documentElement.style.setProperty(VARIABLE, "0");
        window.dispatchEvent(new Event("resize"));
      });
      expect(fijado()).toBeNull();
      expect(enCapa()).toBeNull();
      expect(titulo).toHaveFocus();
      expect(silice()).toHaveAccessibleName("Sílice, abrir los módulos");
    });

    test("fijado en la cuenta pero sin ancho para fijarlo: no se pinta hasta pulsar «Sílice», y sale en capa sin «Fijar»", async () => {
      const u = userEvent.setup();
      document.documentElement.style.setProperty(VARIABLE, "0");
      const { container } = montarCon(sesionDe("ana", "obras", true), "/hoja");
      await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
      expect(fijado()).toBeNull();
      expect(enCapa()).toBeNull();
      expect(container.querySelector(".silice-marco")).not.toHaveClass("silice-marco--fijado");
      await u.click(screen.getByRole("button", { name: "Sílice, abrir los módulos" }));
      expect(enCapa()).toBeInTheDocument();
      expect(within(enCapa()!).queryByRole("button", { name: "Fijar" })).not.toBeInTheDocument();
    });

    test("fijado en la cuenta y con ancho: se pinta fijado al cargar; Esc no pinta capa y «Sílice» lleva el foco al módulo actual", async () => {
      const u = userEvent.setup();
      document.documentElement.style.setProperty(VARIABLE, "1");
      const { container } = montarCon(sesionDe("ana", "obras", true), "/hoja");
      await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
      expect(fijado()).toBeInTheDocument();
      expect(container.querySelector(".silice-marco")).toHaveClass("silice-marco--fijado");
      screen.getByRole("main").focus();
      await u.keyboard("{Escape}");
      expect(enCapa()).toBeNull();
      expect(fijado()).toBeInTheDocument();
      await u.click(silice());
      expect(fijado()).toBeInTheDocument();
      expect(enCapa()).toBeNull();
      expect(within(fijado()!).getByRole("link", { name: "Presupuestos y obras" })).toHaveFocus();
      expect(cuerposPut()).toEqual([]);
    });

    test("las áreas del sidebar son las mismas pantallas que la barra, cada título una sola vez", async () => {
      const u = userEvent.setup();
      montarCon(sesionDe("ana", "obras"), "/hoja");
      await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
      const deLaBarra: string[] = [];
      for (const area of areasDeLaBarra()) {
        if (area.tagName === "BUTTON") {
          await u.click(area);
          deLaBarra.push(...within(document.getElementById(area.getAttribute("aria-controls")!)!).getAllByRole("link").map((a) => a.getAttribute("href")!));
        } else deLaBarra.push(area.getAttribute("href")!);
      }
      await u.click(document.body);
      await u.click(silice());
      const areas = areasDelSidebar();
      expect(within(areas).getByText("Áreas de Presupuestos y obras")).toBeInTheDocument();
      expect(within(areas).getAllByRole("link").map((a) => a.getAttribute("href"))).toEqual(deLaBarra);
      for (const titulo of titulosDelSidebar()) expect(within(enCapa()!).getAllByText(titulo)).toHaveLength(1);
    });

    test("el pie trae «Acerca de Sílice» y no «Administración» con ana; con el administrador las dos", async () => {
      const u = userEvent.setup();
      const { unmount } = montarCon(sesionDe("ana", "obras"), "/hoja");
      await screen.findByRole("heading", { level: 1, name: "Hoja del proyecto" });
      await u.click(silice());
      expect(within(enCapa()!).getByRole("link", { name: "Acerca de Sílice" })).toBeInTheDocument();
      expect(within(enCapa()!).queryByRole("link", { name: "Administración" })).not.toBeInTheDocument();
      expect(within(enCapa()!).getByText("Sesión de Ana Pérez")).toBeInTheDocument();
      unmount();
      montarCon(sesionDe("admin", "obras"), "/obras");
      await screen.findByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" });
      await u.click(silice());
      await u.click(within(enCapa()!).getByRole("link", { name: "Administración" }));
      expect(await screen.findByRole("heading", { level: 1, name: "Administración" })).toBeInTheDocument();
      expect(enCapa()).toBeNull();
      await u.click(silice());
      await u.click(within(enCapa()!).getByRole("link", { name: "Acerca de Sílice" }));
      expect(await screen.findByRole("heading", { level: 1, name: "Acerca de Sílice" })).toBeInTheDocument();
    });

    // Foco 4 y condicion del arbitro de MOD-1: sin escribir direcciones, solo con clics en el sidebar (modulos y pie) y
    // en la barra de cada modulo, cada cuenta llega a TODAS sus pantallas y a ninguna otra. Oraculo escrito a mano.
    test.each([
      [
        "ana",
        [
          "/auditoria",
          "/libros",
          "/historial",
          "/obras",
          "/hoja",
          "/elaborar",
          "/tablero",
          "/entregar",
          "/componer",
          "/catalogo",
          "/similares",
          "/mercado",
          "/actualizacion",
          "/historico",
          "/simulador",
          "/aprobar",
          "/control",
          "/reajuste",
          "/escenarios",
          "/produccion",
          "/existencias",
          "/acerca",
        ],
      ],
      ["rita", ["/auditoria", "/libros", "/revisar", "/historial", "/obras", "/tablero", "/catalogo", "/historico", "/aprobar", "/acerca"]],
      ["admin", ["/obras", "/precios_empresa", "/indices", "/produccion", "/existencias", "/administracion", "/acerca"]],
    ] as const)("foco 4: %s alcanza toda pantalla suya con clics en el sidebar y la barra", async (rol, esperadas) => {
      const u = userEvent.setup();
      montarCon(sesionDe(rol), "/");
      await screen.findByRole("heading", { level: 1 });
      const alcanzadas: string[] = [];
      await u.click(silice());
      const modulos = [...enCapa()!.querySelectorAll<HTMLAnchorElement>(".silice-sidebar__modulos a")].map((a) => a.getAttribute("href")!);
      const pie = [...enCapa()!.querySelectorAll<HTMLAnchorElement>(".silice-sidebar__pie a")].map((a) => a.getAttribute("href")!);
      await u.click(silice());
      for (const ruta of modulos) {
        await u.click(silice());
        await u.click(enCapa()!.querySelector<HTMLElement>(`.silice-sidebar__modulos a[href="${ruta}"]`)!);
        const titulo = REGISTRO.find((p) => `/${p.id}` === ruta)!.titulo;
        await screen.findByRole("heading", { level: 1, name: titulo });
        alcanzadas.push(ruta);
        for (const area of areasDeLaBarra()) {
          if (area.tagName === "BUTTON") {
            await u.click(area);
            alcanzadas.push(
              ...within(document.getElementById(area.getAttribute("aria-controls")!)!)
                .getAllByRole("link")
                .map((a) => a.getAttribute("href")!),
            );
            await u.click(area);
          } else alcanzadas.push(area.getAttribute("href")!);
        }
      }
      alcanzadas.push(...pie);
      // Cada pantalla una vez por camino propio: el inicio de cada modulo sale en el sidebar y en «Inicio» de su barra.
      const sinInicios = alcanzadas.filter((r, i) => !(modulos.includes(r) && alcanzadas.indexOf(r) !== i));
      expect(new Set(sinInicios).size).toBe(sinInicios.length);
      expect([...new Set(alcanzadas)].sort()).toEqual([...esperadas].sort());
    });

    describe("foco 3: confirmación al salir con trabajo sin guardar", () => {
      test("elegir «Auditoría» en el sidebar pregunta; «Quedarme» no navega ni guarda; «Salir y descartar» navega", async () => {
        const u = userEvent.setup();
        montarCon(sesionDe("ana", "obras"), "/componer", CON_PAGINAS_PROPIAS);
        await screen.findByRole("heading", { level: 1, name: "Componer una partida" });
        await u.click(silice());
        const auditoria = within(enCapa()!).getByRole("link", { name: "Auditoría" });
        await u.click(auditoria);
        const dialogo = screen.getByRole("dialog", { name: "Cambios sin guardar" });
        expect(dialogo).toHaveAccessibleDescription(
          "Tiene cambios sin guardar en Componer una partida. Si sale de esta pantalla, se perderán.",
        );
        await u.click(within(dialogo).getByRole("button", { name: "Quedarme" }));
        expect(screen.queryByRole("dialog", { name: "Cambios sin guardar" })).not.toBeInTheDocument();
        expect(screen.getByRole("heading", { level: 1, name: "Componer una partida" })).toBeInTheDocument();
        expect(auditoria).toHaveFocus();
        await new Promise((r) => setTimeout(r, 30));
        expect(cuerposPut()).toEqual([]);
        await u.click(auditoria);
        await u.click(screen.getByRole("button", { name: "Salir y descartar" }));
        expect(await screen.findByRole("heading", { level: 1, name: "Inicio de auditoría" })).toBeInTheDocument();
        expect(enCapa()).toBeNull();
        expect(formulariosSucios()).toEqual([]);
        await waitFor(() => expect(cuerposPut()).toEqual(['{"modulo":"auditoria"}']));
      });

      test("lo mismo con el enlace «Inicio» de la barra y con un enlace del panel «Mercado»", async () => {
        const u = userEvent.setup();
        montarCon(sesionDe("ana", "obras"), "/componer", CON_PAGINAS_PROPIAS);
        await screen.findByRole("heading", { level: 1, name: "Componer una partida" });
        await u.click(within(menu()).getByRole("link", { name: "Inicio" }));
        expect(screen.getByRole("dialog", { name: "Cambios sin guardar" })).toBeInTheDocument();
        await u.click(screen.getByRole("button", { name: "Quedarme" }));
        expect(screen.getByRole("heading", { level: 1, name: "Componer una partida" })).toBeInTheDocument();
        await u.click(within(menu()).getByRole("button", { name: "Mercado" }));
        await u.click(within(menu()).getByRole("link", { name: "Actualizar precios" }));
        expect(screen.getByRole("dialog", { name: "Cambios sin guardar" })).toBeInTheDocument();
        await u.click(screen.getByRole("button", { name: "Quedarme" }));
        expect(screen.getByRole("heading", { level: 1, name: "Componer una partida" })).toBeInTheDocument();
        await u.click(within(menu()).getByRole("button", { name: "Mercado" }));
        await u.click(within(menu()).getByRole("link", { name: "Actualizar precios" }));
        await u.click(screen.getByRole("button", { name: "Salir y descartar" }));
        expect(await screen.findByRole("heading", { level: 1, name: "Actualizar precios" })).toBeInTheDocument();
        expect(formulariosSucios()).toEqual([]);
      });

      test("volver a /componer estando en /componer no pregunta", async () => {
        const u = userEvent.setup();
        montarCon(sesionDe("ana", "obras"), "/componer", CON_PAGINAS_PROPIAS);
        await screen.findByRole("heading", { level: 1, name: "Componer una partida" });
        await u.click(within(menu()).getByRole("button", { name: "Partidas" }));
        await u.click(within(menu()).getByRole("link", { name: "Componer una partida" }));
        expect(screen.queryByRole("dialog", { name: "Cambios sin guardar" })).not.toBeInTheDocument();
        expect(screen.getByRole("heading", { level: 1, name: "Componer una partida" })).toBeInTheDocument();
        expect(formulariosSucios()).toEqual(["componer"]);
      });

      test("atrás/adelante del navegador no se intercepta (declarado en el diseño, §12.5)", async () => {
        montarCon(sesionDe("ana", "obras"), "/obras", CON_PAGINAS_PROPIAS);
        await screen.findByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" });
        act(() => void historia.ir!("/componer"));
        await screen.findByRole("heading", { level: 1, name: "Componer una partida" });
        act(() => void historia.ir!(-1));
        expect(await screen.findByRole("heading", { level: 1, name: "Inicio de presupuestos y obras" })).toBeInTheDocument();
        expect(screen.queryByRole("dialog", { name: "Cambios sin guardar" })).not.toBeInTheDocument();
      });
    });
  });

  // VB-15 (auditoria visual del bloque B). La capa de VB-14 la reemplaza el sidebar de modulos (MOD-2, mas abajo).
  describe("titulo del documento", () => {
    test("document.title es «Página · Sílice» con la página actual y cambia al navegar", async () => {
      const usuario = userEvent.setup();
      montar(sesionCon(), "/tablero");
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      expect(document.title).toBe("Tablero del proyecto · Sílice");
      await usuario.click(within(menu()).getByRole("link", { name: "Partidas" }));
      await waitFor(() => expect(document.title).toBe("Catálogo de partidas e insumos · Sílice"));
    });

    test("sin página para la ruta el título queda en «Sílice»", async () => {
      render(
        <MemoryRouter initialEntries={["/"]}>
          <Shell sesion={sesionCon()} alSalir={alSalir} alExpirar={alExpirar} paginas={[]} />
        </MemoryRouter>,
      );
      await screen.findByText("No hay pantallas disponibles en esta interfaz");
      expect(document.title).toBe("Sílice");
    });
  });

  // Plan de modulos, MOD-3b: el selector «Proyecto» del panel «Carpeta y proyecto» paso a ser el selector de obra.
  describe("selector de obra", () => {
    test("lista las obras y empieza sin ninguna elegida", async () => {
      const usuario = userEvent.setup();
      montar();
      const boton = await botonObra();
      expect(boton).toHaveTextContent("Obra: sin elegir");
      await usuario.click(boton);
      await waitFor(() => expect(obrasDeLaLista()).toEqual(["Clínica Norte", "Galpón (sin versión guardada)"]));
      expect(screen.queryByRole("button", { name: /^Clínica Norte/ })).not.toHaveAttribute("aria-current");
    });

    test("la elegida llega a las paginas por el contexto, se ve en la barra y no se guarda en el navegador", async () => {
      const usuario = userEvent.setup();
      const espiaSet = vi.spyOn(Storage.prototype, "setItem");
      montar();
      expect(await screen.findByText("proyecto=ninguno")).toBeInTheDocument();
      await usuario.click(await botonObra());
      await usuario.click(await screen.findByRole("button", { name: /^Galpón/ }));
      expect(await screen.findByText("proyecto=P-02")).toBeInTheDocument();
      expect(await botonObra()).toHaveAccessibleName("Obra: Galpón. Cambiar obra");
      expect(espiaSet).not.toHaveBeenCalled();
      espiaSet.mockRestore();
    });

    test("al cambiar de carpeta se olvida la obra elegida", async () => {
      const usuario = userEvent.setup();
      montar();
      await usuario.click(await botonObra());
      await usuario.click(await screen.findByRole("button", { name: /^Clínica Norte/ }));
      expect(await screen.findByText("proyecto=P-01")).toBeInTheDocument();
      await abrirEnElDialogo(usuario, "arenaza");
      expect(await screen.findByText("proyecto=ninguno")).toBeInTheDocument();
    });

    test("sin permiso para listar obras (403) el panel no las lista y no hay error", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockImplementation(async (entrada, init) => {
        const ruta = String(entrada);
        if (ruta === "/v1/casos" && (init?.method ?? "GET") === "GET") return json(CASOS);
        if (ruta === "/v1/proyectos") return json({ detalle: "Su cuenta no tiene permiso." }, 403);
        return json({ detalle: "No encontrado." }, 404);
      });
      montar();
      await waitFor(() => expect(fetchFalso.mock.calls.some((c) => String(c[0]) === "/v1/proyectos")).toBe(true));
      await usuario.click(await botonObra());
      expect(screen.queryByRole("list", { name: "Obras de la carpeta de trabajo" })).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    // VB-20: el codigo es un numero interno; la persona elige por el nombre. Si dos obras se llaman igual, el codigo es
    // lo unico que las distingue y se agrega entre parentesis.
    test("dos obras con el mismo nombre se distinguen por su código", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockImplementation(async (entrada, init) => {
        const ruta = String(entrada);
        if (ruta === "/v1/casos" && (init?.method ?? "GET") === "GET") return json(CASOS);
        if (ruta === "/v1/proyectos")
          return json([
            { codigo: "3", nombre: "OBRA-GENERADA", version_vigente: 1, actualizado: null, cliente: "", ubicacion: "" },
            { codigo: "4", nombre: "OBRA-GENERADA", version_vigente: 1, actualizado: null, cliente: "", ubicacion: "" },
            { codigo: "5", nombre: "Galpón", version_vigente: 1, actualizado: null, cliente: "", ubicacion: "" },
          ]);
        return json({ detalle: "No encontrado." }, 404);
      });
      montar();
      await usuario.click(await botonObra());
      await waitFor(() => expect(obrasDeLaLista()).toEqual(["OBRA-GENERADA (3)", "OBRA-GENERADA (4)", "Galpón"]));
    });

    // VB-9: sin `leer_proyecto` la API contesta 403; no se pide.
    test("una cuenta sin la acción leer_proyecto no pide la lista de obras", async () => {
      montar(sesionCon({ acciones: ["administrar_cuentas", "cambiar_caso"] }), "/acerca");
      await screen.findByRole("heading", { name: "Otra pantalla" });
      await waitFor(() => expect(fetchFalso.mock.calls.some((c) => String(c[0]) === "/v1/casos")).toBe(true));
      expect(fetchFalso.mock.calls.some((c) => String(c[0]) === "/v1/proyectos")).toBe(false);
    });

    test("sin ninguna pagina disponible para la cuenta, dice que no hay pantallas en esta interfaz", async () => {
      render(
        <MemoryRouter initialEntries={["/"]}>
          <Shell sesion={sesionCon()} alSalir={alSalir} alExpirar={alExpirar} paginas={[]} />
        </MemoryRouter>,
      );
      expect(await screen.findByText("No hay pantallas disponibles en esta interfaz")).toBeInTheDocument();
      expect(screen.queryByText(/clásica/i)).toBeNull();
    });
  });
  // VD-7: cuando la accion quita el control que tenia el foco, el foco cae a <body>. Una prueba de jsdom no ve la
  // geometria pero si el foco: cada una de estas debe fallar si se quita la linea que lo mueve.
  describe("el foco no se pierde cuando la accion quita el control", () => {
    function Origen() {
      const ir = useNavigate();
      return (
        <div>
          <h1>Pantalla de origen</h1>
          <button type="button" onClick={() => void ir("/destino")}>
            Ir al destino
          </button>
        </div>
      );
    }
    const Destino = () => <h1>Pantalla de destino</h1>;
    const InicioPrueba = () => <h1>Inicio de prueba</h1>;
    // Las dos en el area «Partidas» (su panel) y un inicio del modulo para la direccion de entrada.
    const DOS: PaginaDef[] = [
      { id: "origen", titulo: "Origen de prueba", enUnaLinea: "Pantalla de prueba", seccion: "Trabajo", accion: null, ubicacion: { modulo: "obras", area: "partidas" }, cargar: async () => ({ default: Origen }) },
      { id: "destino", titulo: "Destino de prueba", enUnaLinea: "Pantalla de prueba", seccion: "Trabajo", accion: null, ubicacion: { modulo: "obras", area: "partidas" }, cargar: async () => ({ default: Destino }) },
      { id: "obras", titulo: "Inicio de prueba", enUnaLinea: "Pantalla de prueba", seccion: "Trabajo", accion: null, ubicacion: { modulo: "obras", area: "inicio" }, cargar: async () => ({ default: InicioPrueba }) },
    ];
    function montarDos() {
      return render(
        <MemoryRouter initialEntries={["/origen"]}>
          <Shell sesion={sesionCon()} alSalir={alSalir} alExpirar={alExpirar} paginas={DOS} />
        </MemoryRouter>,
      );
    }

    test("un botón de la página que lleva a otra deja el foco en el único h1 de la página nueva", async () => {
      const usuario = userEvent.setup();
      montarDos();
      await usuario.click(await screen.findByRole("button", { name: "Ir al destino" }));
      const titulo = await screen.findByRole("heading", { name: "Pantalla de destino" });
      await waitFor(() => expect(titulo).toHaveFocus());
      expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
      expect(titulo).toHaveAttribute("tabindex", "-1");
    });

    test("elegir otra pantalla en el panel de un área lleva el foco al h1 de la nueva (el panel se cierra)", async () => {
      const usuario = userEvent.setup();
      montarDos();
      await screen.findByRole("heading", { name: "Pantalla de origen" });
      await usuario.click(within(menu()).getByRole("button", { name: "Partidas" }));
      await usuario.click(within(menu()).getByRole("link", { name: "Destino de prueba" }));
      const titulo = await screen.findByRole("heading", { name: "Pantalla de destino" });
      await waitFor(() => expect(titulo).toHaveFocus());
      expect(within(menu()).queryByRole("region", { name: "Partidas" })).not.toBeInTheDocument();
    });

    test("elegir en el panel la pantalla en la que ya está deja el foco en su h1, no en <body>", async () => {
      const usuario = userEvent.setup();
      montarDos();
      const titulo = await screen.findByRole("heading", { name: "Pantalla de origen" });
      await usuario.click(within(menu()).getByRole("button", { name: "Partidas" }));
      await usuario.click(within(menu()).getByRole("link", { name: "Origen de prueba" }));
      expect(within(menu()).queryByRole("region", { name: "Partidas" })).not.toBeInTheDocument();
      await waitFor(() => expect(titulo).toHaveFocus());
    });

    test("un enlace directo de la barra conserva el foco: solo se mueve si se perdió", async () => {
      const usuario = userEvent.setup();
      // En Producción, Inicio y Existencias tienen una sola pantalla: son enlaces que siguen en la barra tras navegar.
      const directas: PaginaDef[] = [
        { ...DOS[0], id: "produccion", titulo: "Inicio de producción", ubicacion: { modulo: "produccion", area: "inicio" } },
        { ...DOS[1], id: "existencias", titulo: "Existencias de prueba", ubicacion: { modulo: "produccion", area: "existencias" } },
      ];
      render(
        <MemoryRouter initialEntries={["/produccion"]}>
          <Shell sesion={sesionCon()} alSalir={alSalir} alExpirar={alExpirar} paginas={directas} />
        </MemoryRouter>,
      );
      await screen.findByRole("heading", { name: "Pantalla de origen" });
      const enlace = within(menu()).getByRole("link", { name: "Existencias" });
      await usuario.click(enlace);
      await screen.findByRole("heading", { name: "Pantalla de destino" });
      await new Promise((r) => setTimeout(r, 80));
      expect(enlace).toHaveFocus();
    });

    test("al cargar la primera vez no roba el foco: «Saltar al contenido» sigue siendo el primer Tab", async () => {
      montarDos();
      await screen.findByRole("heading", { name: "Pantalla de origen" });
      await new Promise((r) => setTimeout(r, 80));
      expect(document.body).toHaveFocus();
    });

    // Ronda 1 del arbitro: la entrada real es «/» (o una ruta que no existe) y ambas REDIRIGEN con `replace` al inicio
    // del modulo; eso es la carga inicial, no un cambio de pagina: el foco sigue en <body> y el primer Tab es «Saltar».
    test.each(["/", "/inicio", "/ruta-inexistente"])("al cargar en %s (redirige al inicio del módulo) no roba el foco", async (entrada) => {
      const usuario = userEvent.setup();
      render(
        <MemoryRouter initialEntries={[entrada]}>
          <Shell sesion={sesionCon()} alSalir={alSalir} alExpirar={alExpirar} paginas={DOS} />
        </MemoryRouter>,
      );
      await screen.findByRole("heading", { name: "Inicio de prueba" });
      await new Promise((r) => setTimeout(r, 120));
      expect(document.body).toHaveFocus();
      await usuario.tab();
      expect(screen.getByRole("button", { name: "Saltar al contenido" })).toHaveFocus();
    });

    // Acerca: el h1 del esqueleto recibia el foco y la pagina real lo sustituia, dejando el foco en <body>.
    test("si la página nueva dibuja primero un esqueleto con h1, el foco va al h1 real", async () => {
      const usuario = userEvent.setup();
      function Lenta() {
        const [lista, setLista] = useState(false);
        useEffect(() => {
          const t = setTimeout(() => setLista(true), 60);
          return () => clearTimeout(t);
        }, []);
        return lista ? <h1>Pantalla lenta lista</h1> : <EsqueletoPagina titulo="Pantalla lenta" />;
      }
      const TRES: PaginaDef[] = [
        ...DOS,
        { id: "lenta", titulo: "Lenta de prueba", enUnaLinea: "Pantalla de prueba", seccion: "Trabajo", accion: null, ubicacion: { modulo: "obras", area: "partidas" }, cargar: async () => ({ default: Lenta }) },
      ];
      function Va() {
        const ir = useNavigate();
        return (
          <button type="button" onClick={() => void ir("/lenta")}>
            Ir a la lenta
          </button>
        );
      }
      TRES[0] = { ...DOS[0], cargar: async () => ({ default: Va }) };
      render(
        <MemoryRouter initialEntries={["/origen"]}>
          <Shell sesion={sesionCon()} alSalir={alSalir} alExpirar={alExpirar} paginas={TRES} />
        </MemoryRouter>,
      );
      await usuario.click(await screen.findByRole("button", { name: "Ir a la lenta" }));
      const real = await screen.findByRole("heading", { name: "Pantalla lenta lista" });
      await waitFor(() => expect(real).toHaveFocus());
    });

    // Tarea 6 del plan de la barra: al terminar, el foco va al h1 de la pagina (ya no hay un enlace del menu al que volver).
    test("«Terminar recorrido» con Enter deja el foco en el h1 de la página, no en <body>", async () => {
      const usuario = userEvent.setup();
      montar();
      const titulo = await screen.findByRole("heading", { name: "Pantalla del tablero" });
      act(() => iniciarRecorrido(RECORRIDO_AUDITAR));
      onTestFinished(() => terminarRecorrido());
      const columna = screen.getByRole("complementary", { name: "Recorrido" });
      within(columna).getByRole("button", { name: "Terminar recorrido" }).focus();
      await usuario.keyboard("{Enter}");
      expect(screen.queryByRole("complementary", { name: "Recorrido" })).not.toBeInTheDocument();
      expect(titulo).toHaveFocus();
    });
  });
});
