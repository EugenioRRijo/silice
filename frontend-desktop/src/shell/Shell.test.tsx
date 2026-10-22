import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useNavigate } from "react-router";
import { afterEach, beforeEach, describe, expect, onTestFinished, test, vi } from "vitest";
import { fijarCsrf } from "../api/cliente";
import type { SesionRespuesta } from "../api/tipos";
import { alertaConTexto } from "../test/ayudas";
import { useState, useEffect } from "react";
import { useAplicacion } from "./contexto";
import { EsqueletoPagina } from "../comun/EsqueletoPagina";
import { RECORRIDO_AUDITAR, iniciarRecorrido, recorridoEnCurso, terminarRecorrido } from "./recorrido";
import { Shell } from "./Shell";
import type { PaginaDef } from "./rutas";

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

const PAGINAS: PaginaDef[] = [
  { id: "tablero", titulo: "Tablero del proyecto", seccion: "Trabajo", accion: "leer_proyecto", cargar: async () => ({ default: PaginaA }) },
  { id: "catalogo", titulo: "Catálogo de partidas e insumos", seccion: "Trabajo", accion: "leer_proyecto", cargar: CARGAR_B },
  { id: "control", titulo: "Control de obra", seccion: "Trabajo", accion: "control_de_obra", cargar: CARGAR_B },
  { id: "acerca", titulo: "Acerca de Sílice", seccion: "Trabajo", accion: null, cargar: CARGAR_B },
  { id: "revisar", titulo: "Revisar un paquete", seccion: "Revisión", accion: "revisar_paquete", cargar: CARGAR_B },
  { id: "escenarios", titulo: "Escenarios de sensibilidad", seccion: "Investigación", accion: "editar_hoja", cargar: CARGAR_B },
];

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
      return json({ detalle: "No encontrado." }, 404);
    });
    alSalir = vi.fn<() => void>();
    alExpirar = vi.fn<() => void>();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function montar(sesion = sesionCon(), ruta = "/tablero") {
    return render(
      <MemoryRouter initialEntries={[ruta]}>
        <Shell sesion={sesion} alSalir={alSalir} alExpirar={alExpirar} paginas={PAGINAS} />
      </MemoryRouter>,
    );
  }

  function menu() {
    return screen.getByRole("navigation", { name: "Menú principal" });
  }

  describe("cabecera", () => {
    test("muestra el nombre de la persona y Salir llama a alSalir", async () => {
      const usuario = userEvent.setup();
      montar();
      expect(await screen.findByText("Ana Pérez")).toBeInTheDocument();
      await usuario.click(screen.getByRole("button", { name: /^Salir/ }));
      expect(alSalir).toHaveBeenCalled();
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
  });

  describe("menu", () => {
    test("agrupa por area segun las acciones de la sesion, cada una con su descripcion a la vista", async () => {
      montar();
      const nav = menu();
      const rotulos = [...nav.querySelectorAll(".silice-menu__rotulo")].map((h) => h.textContent);
      expect(rotulos).toEqual(["Crear", "Más"]); // sin revisar_paquete ni operar_arenera no hay Auditar ni Producción
      expect(within(nav).getByText("APU, presupuestos y entregas")).toBeInTheDocument();
      expect(within(nav).getByText("Precios, obra, análisis y ajustes")).toBeInTheDocument();
      expect(within(nav).queryByText("Control de obra")).not.toBeInTheDocument(); // sin control_de_obra
      expect(within(nav).getByText("Acerca de Sílice")).toBeInTheDocument(); // sin accion: toda cuenta la ve
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
    });

    test("«Más» viene plegado, se abre con su boton y se abre solo si la pagina actual es de ahi", async () => {
      const usuario = userEvent.setup();
      montar();
      const boton = within(menu()).getByRole("button", { name: "Más" });
      expect(boton).toHaveAttribute("aria-expanded", "false");
      expect(within(menu()).queryByRole("link", { name: /Escenarios/ })).not.toBeInTheDocument();
      await usuario.click(boton);
      expect(boton).toHaveAttribute("aria-expanded", "true");
      expect(within(menu()).getByText("Escenarios de sensibilidad")).toBeVisible();
      await usuario.click(boton);
      expect(boton).toHaveAttribute("aria-expanded", "false");
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
    });

    test("estando en una pagina de «Más» ese grupo ya esta abierto", async () => {
      const paginas: PaginaDef[] = [
        ...PAGINAS,
        { id: "indices", titulo: "Índices del BCV", seccion: "Trabajo", accion: "leer_proyecto", cargar: async () => ({ default: PaginaA }) },
      ];
      render(
        <MemoryRouter initialEntries={["/indices"]}>
          <Shell sesion={sesionCon()} alSalir={alSalir} alExpirar={alExpirar} paginas={paginas} />
        </MemoryRouter>,
      );
      expect(within(menu()).getByRole("button", { name: "Más" })).toHaveAttribute("aria-expanded", "true");
      expect(within(menu()).getByRole("link", { name: "Índices del BCV" })).toBeVisible();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
    });

    test("las herramientas principales van arriba, en su orden, con su linea de ayuda, y solo las que la cuenta puede usar", async () => {
      const migrada = async () => ({ default: PaginaA });
      const paginas: PaginaDef[] = [
        { id: "libros", titulo: "Libro de la empresa", seccion: "Revisión", accion: "leer_proyecto", cargar: migrada },
        { id: "componer", titulo: "Componer una partida", seccion: "Trabajo", accion: "editar_hoja", cargar: migrada },
        { id: "existencias", titulo: "Existencias de la arenera", seccion: "Trabajo", accion: "operar_arenera", cargar: migrada },
      ];
      render(
        <MemoryRouter initialEntries={["/libros"]}>
          <Shell sesion={sesionCon()} alSalir={alSalir} alExpirar={alExpirar} paginas={paginas} />
        </MemoryRouter>,
      );
      const nav = menu();
      const panel = within(nav).getByText("Herramientas principales").closest("li") as HTMLElement;
      expect(within(panel).getAllByRole("link").map((a) => a.getAttribute("aria-label"))).toEqual([
        "Libro de la empresa",
        "Componer una partida",
      ]); // la cuenta de ana no opera la arenera; la herramienta lleva el nombre de su pantalla
      expect(within(panel).getByText("Suba un Excel y vea lo que no cuadra")).toBeInTheDocument();
      expect(within(panel).getByRole("link", { name: "Componer una partida" })).toHaveAttribute("href", "/componer");
      expect(within(panel).getByRole("link", { name: "Libro de la empresa" })).toHaveAccessibleDescription(
        "Suba un Excel y vea lo que no cuadra",
      );
      // El panel va antes que las areas.
      const rotulos = [...nav.querySelectorAll(".silice-menu__rotulo")].map((h) => h.textContent);
      expect(rotulos[0]).toBe("Herramientas principales");
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
    });

    test("sin ninguna herramienta principal disponible el panel no se pinta", async () => {
      montar();
      expect(within(menu()).queryByText("Herramientas principales")).not.toBeInTheDocument();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
    });

    test("el recorrido en curso aparece en el menu y se cierra desde ahi", async () => {
      const usuario = userEvent.setup();
      montar();
      expect(within(menu()).queryByRole("region", { name: "Recorrido en curso" })).not.toBeInTheDocument();
      act(() => iniciarRecorrido(RECORRIDO_AUDITAR));
      onTestFinished(() => terminarRecorrido());
      const region = within(menu()).getByRole("region", { name: "Recorrido en curso" });
      await usuario.click(within(region).getByRole("button", { name: "Terminar recorrido" }));
      expect(within(menu()).queryByRole("region", { name: "Recorrido en curso" })).not.toBeInTheDocument();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
    });

    test("la descripcion de cada area esta ligada a su lista", async () => {
      montar();
      const lista = within(menu()).getByText("Tablero del proyecto").closest("ul") as HTMLElement;
      expect(lista).toHaveAccessibleDescription("APU, presupuestos y entregas");
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
    });

    test("en modo entrega desaparece Investigacion", async () => {
      montar(sesionCon({ modo_entrega: true }));
      const nav = menu();
      expect(within(nav).queryByText("Investigación")).not.toBeInTheDocument();
      expect(within(nav).queryByText("Escenarios de sensibilidad")).not.toBeInTheDocument();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
    });

    test("la pagina migrada es un enlace y marca la actual", async () => {
      montar();
      const enlace = within(menu()).getByRole("link", { name: "Tablero del proyecto" });
      expect(enlace).toHaveAttribute("href", "/tablero");
      expect(enlace).toHaveAttribute("aria-current", "page");
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
    });

    test("toda pagina del menu es un enlace de esta interfaz: ni «clásica» ni enlaces fuera de ella", async () => {
      montar();
      const nav = menu();
      expect(nav).not.toHaveTextContent(/clásica/i);
      expect(nav.querySelector(".silice-menu__pendiente, .silice-menu__grupo")).toBeNull();
      expect(nav.querySelector("a[target=_blank]")).toBeNull();
      const enlace = within(nav).getByRole("link", { name: /Catálogo de partidas e insumos/ });
      expect(enlace).toHaveAttribute("href", "/catalogo");
      expect(within(nav).queryByText("Catálogo de partidas e insumos")?.closest("[aria-disabled]")).toBeNull();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
    });

    test("se recorre con el teclado: Tab llega al enlace y Enter cambia de pagina", async () => {
      // En pantalla ancha (lg) el menu esta siempre abierto; en angosta Carbon lo marca inert hasta abrirlo.
      const original = window.matchMedia;
      Object.defineProperty(window, "matchMedia", {
        configurable: true,
        value: (consulta: string) => ({ ...original(consulta), matches: true }),
      });
      onTestFinished(() => {
        Object.defineProperty(window, "matchMedia", { configurable: true, value: original });
      });
      const usuario = userEvent.setup();
      const paginas: PaginaDef[] = [
        ...PAGINAS,
        {
          id: "libros",
          titulo: "Libro de la empresa",
          seccion: "Revisión",
          accion: "leer_proyecto",
          cargar: async () => ({ default: () => <h1>Pantalla del libro</h1> }),
        },
      ];
      render(
        <MemoryRouter initialEntries={["/tablero"]}>
          <Shell sesion={sesionCon()} alSalir={alSalir} alExpirar={alExpirar} paginas={paginas} />
        </MemoryRouter>,
      );
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      // La herramienta principal y su area llevan el mismo nombre: se prueba con el de su area (el ultimo).
      const enlace = within(menu()).getAllByRole("link", { name: "Libro de la empresa" }).at(-1)!;
      for (let i = 0; i < 40 && document.activeElement !== enlace; i++) await usuario.tab();
      expect(enlace).toHaveFocus();
      await usuario.keyboard("{Enter}");
      expect(await screen.findByRole("heading", { name: "Pantalla del libro" })).toBeInTheDocument();
    });
  });

  describe("fin de sesion y recorrido", () => {
    test("Salir cierra el recorrido en curso", async () => {
      const usuario = userEvent.setup();
      montar();
      act(() => iniciarRecorrido(RECORRIDO_AUDITAR));
      onTestFinished(() => terminarRecorrido());
      expect(within(menu()).getByRole("region", { name: "Recorrido en curso" })).toBeInTheDocument();
      await usuario.click(screen.getByRole("button", { name: /^Salir/ }));
      expect(alSalir).toHaveBeenCalled();
      expect(within(menu()).queryByRole("region", { name: "Recorrido en curso" })).not.toBeInTheDocument();
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
      const selector = await screen.findByRole("combobox", { name: "Caso" });
      await waitFor(() => expect(selector).toHaveValue("clinica"));
      await usuario.selectOptions(selector, "arenaza");
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

    test("la raiz lleva a la primera pagina migrada que la persona puede ver", async () => {
      montar(sesionCon(), "/");
      expect(await screen.findByRole("heading", { name: "Pantalla del tablero" })).toBeInTheDocument();
    });

    test("una ruta desconocida vuelve a la raiz", async () => {
      montar(sesionCon(), "/no-existe");
      expect(await screen.findByRole("heading", { name: "Pantalla del tablero" })).toBeInTheDocument();
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

  describe("selector de caso", () => {
    test("lista los casos y deja elegido el actual", async () => {
      montar();
      const selector = await screen.findByRole("combobox", { name: "Caso" });
      await waitFor(() => expect(selector).toHaveValue("clinica"));
      expect(within(selector).getAllByRole("option").map((o) => o.textContent)).toEqual(["clinica", "arenaza"]);
    });

    test("cambiar el caso hace POST /v1/casos/actual con el token y avisa que el cambio vive hasta reiniciar la API", async () => {
      const usuario = userEvent.setup();
      montar();
      const selector = await screen.findByRole("combobox", { name: "Caso" });
      await waitFor(() => expect(selector).toHaveValue("clinica"));
      await usuario.selectOptions(selector, "arenaza");
      await waitFor(() => expect(selector).toHaveValue("arenaza"));
      const llamada = fetchFalso.mock.calls.find((c) => String(c[0]) === "/v1/casos/actual");
      expect(llamada?.[1]?.method).toBe("POST");
      expect(llamada?.[1]?.body).toBe(JSON.stringify({ nombre: "arenaza" }));
      expect(new Headers(llamada?.[1]?.headers).get("X-Silice-CSRF")).toBe("tok");
      expect(await screen.findByText(/vuelve al caso por defecto/i)).toBeInTheDocument();
    });

    test("al cambiar el caso la pagina se vuelve a montar con el caso nuevo", async () => {
      const usuario = userEvent.setup();
      montar();
      expect(await screen.findByText("caso=clinica")).toBeInTheDocument();
      await usuario.selectOptions(await screen.findByRole("combobox", { name: "Caso" }), "arenaza");
      expect(await screen.findByText("caso=arenaza")).toBeInTheDocument();
    });

    test("sin la accion cambiar_caso el selector esta deshabilitado", async () => {
      montar(sesionCon({ acciones: ["leer_proyecto"] }));
      const selector = await screen.findByRole("combobox", { name: "Caso" });
      expect(selector).toBeDisabled();
    });

    test("si la API rechaza el cambio muestra el detalle y deja el caso anterior", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockImplementation(async (entrada, init) => {
        const ruta = String(entrada);
        if (ruta === "/v1/casos" && (init?.method ?? "GET") === "GET") return json(CASOS);
        if (ruta === "/v1/casos/actual") return json({ detalle: "El caso ya no existe." }, 404);
        if (ruta === "/v1/proyectos") return json(PROYECTOS);
        return json({ detalle: "No encontrado." }, 404);
      });
      montar();
      const selector = await screen.findByRole("combobox", { name: "Caso" });
      await waitFor(() => expect(selector).toHaveValue("clinica"));
      await usuario.selectOptions(selector, "arenaza");
      expect(await alertaConTexto()).toHaveTextContent("El caso ya no existe.");
      expect(selector).toHaveValue("clinica");
    });

    test("un 401 al cambiar el caso avisa que la sesion vencio", async () => {
      const usuario = userEvent.setup();
      fetchFalso.mockImplementation(async (entrada, init) => {
        const ruta = String(entrada);
        if (ruta === "/v1/casos" && (init?.method ?? "GET") === "GET") return json(CASOS);
        if (ruta === "/v1/casos/actual") return json({ detalle: "Sin sesión." }, 401);
        if (ruta === "/v1/proyectos") return json(PROYECTOS);
        return json({ detalle: "No encontrado." }, 404);
      });
      montar();
      const selector = await screen.findByRole("combobox", { name: "Caso" });
      await waitFor(() => expect(selector).toHaveValue("clinica"));
      await usuario.selectOptions(selector, "arenaza");
      await waitFor(() => expect(alExpirar).toHaveBeenCalled());
    });
  });

  // VB-14 y VB-15 (auditoria visual del bloque B).
  describe("menu en capa y titulo del documento", () => {
    test("los rótulos de área del menú no son encabezados (el h1 de la página es el primero que se lee)", async () => {
      montar();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      expect(within(menu()).queryAllByRole("heading")).toHaveLength(0);
      expect(menu().querySelectorAll(".silice-menu__rotulo").length).toBeGreaterThan(0);
    });

    test("Esc cierra el menú abierto como capa y devuelve el foco al botón", async () => {
      const usuario = userEvent.setup();
      montar();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      await usuario.click(screen.getByRole("button", { name: "Abrir el menú" }));
      expect(screen.getByRole("button", { name: "Cerrar el menú" })).toHaveAttribute("aria-expanded", "true");
      // El clic deja el foco en el propio boton: se lleva a un enlace del menu para que el regreso se note.
      within(menu()).getAllByRole("link")[0].focus();
      expect(screen.getByRole("button", { name: "Cerrar el menú" })).not.toHaveFocus();
      await usuario.keyboard("{Escape}");
      const boton = screen.getByRole("button", { name: "Abrir el menú" });
      expect(boton).toHaveAttribute("aria-expanded", "false");
      await waitFor(() => expect(boton).toHaveFocus());
    });

    test("Esc con el menú cerrado no mueve el foco", async () => {
      const usuario = userEvent.setup();
      montar();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      await usuario.click(screen.getByRole("button", { name: /^Salir/ }));
      await usuario.keyboard("{Escape}");
      expect(screen.getByRole("button", { name: /^Salir/ })).toHaveFocus();
    });

    test("document.title es «Página · Sílice» con la página actual y cambia al navegar", async () => {
      const usuario = userEvent.setup();
      const dos: PaginaDef[] = [
        ...PAGINAS,
        { id: "libros", titulo: "Libro de la empresa", seccion: "Revisión", accion: "leer_proyecto", cargar: async () => ({ default: PaginaA }) },
      ];
      render(
        <MemoryRouter initialEntries={["/tablero"]}>
          <Shell sesion={sesionCon()} alSalir={alSalir} alExpirar={alExpirar} paginas={dos} />
        </MemoryRouter>,
      );
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      expect(document.title).toBe("Tablero del proyecto · Sílice");
      await usuario.click(screen.getByRole("button", { name: "Abrir el menú" }));
      await usuario.click(within(menu()).getAllByRole("link", { name: "Libro de la empresa" })[0]);
      await waitFor(() => expect(document.title).toBe("Libro de la empresa · Sílice"));
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

  describe("selector de proyecto", () => {
    test("lista los proyectos y empieza sin ninguno elegido", async () => {
      montar();
      const selector = await screen.findByRole("combobox", { name: "Proyecto" });
      await waitFor(() => expect(within(selector).getAllByRole("option")).toHaveLength(3));
      expect(within(selector).getAllByRole("option").map((o) => o.textContent)).toEqual([
        "Sin proyecto",
        "Clínica Norte",
        "Galpón",
      ]);
      expect(selector).toHaveValue("");
    });

    test("el elegido llega a las paginas por el contexto y no se guarda en el navegador", async () => {
      const usuario = userEvent.setup();
      const espiaSet = vi.spyOn(Storage.prototype, "setItem");
      montar();
      expect(await screen.findByText("proyecto=ninguno")).toBeInTheDocument();
      const selector = await screen.findByRole("combobox", { name: "Proyecto" });
      await waitFor(() => expect(within(selector).getAllByRole("option")).toHaveLength(3));
      await usuario.selectOptions(selector, "P-02");
      expect(await screen.findByText("proyecto=P-02")).toBeInTheDocument();
      expect(espiaSet).not.toHaveBeenCalled();
      espiaSet.mockRestore();
    });

    test("al cambiar de caso se olvida el proyecto elegido", async () => {
      const usuario = userEvent.setup();
      montar();
      const proyecto = await screen.findByRole("combobox", { name: "Proyecto" });
      await waitFor(() => expect(within(proyecto).getAllByRole("option")).toHaveLength(3));
      await usuario.selectOptions(proyecto, "P-01");
      expect(await screen.findByText("proyecto=P-01")).toBeInTheDocument();
      await usuario.selectOptions(await screen.findByRole("combobox", { name: "Caso" }), "arenaza");
      expect(await screen.findByText("proyecto=ninguno")).toBeInTheDocument();
    });

    test("sin permiso para listar proyectos (403) el selector no se muestra y no hay error", async () => {
      fetchFalso.mockImplementation(async (entrada, init) => {
        const ruta = String(entrada);
        if (ruta === "/v1/casos" && (init?.method ?? "GET") === "GET") return json(CASOS);
        if (ruta === "/v1/proyectos") return json({ detalle: "Su cuenta no tiene permiso." }, 403);
        return json({ detalle: "No encontrado." }, 404);
      });
      montar();
      await screen.findByRole("combobox", { name: "Caso" });
      await waitFor(() => expect(fetchFalso.mock.calls.some((c) => String(c[0]) === "/v1/proyectos")).toBe(true));
      expect(screen.queryByRole("combobox", { name: "Proyecto" })).not.toBeInTheDocument();
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });

    // VB-20: el codigo es un numero interno; la persona elige por el nombre. Si dos proyectos se llaman igual, el
    // codigo es lo unico que los distingue y se agrega entre parentesis.
    test("dos proyectos con el mismo nombre se distinguen por su código", async () => {
      fetchFalso.mockImplementation(async (entrada, init) => {
        const ruta = String(entrada);
        if (ruta === "/v1/casos" && (init?.method ?? "GET") === "GET") return json(CASOS);
        if (ruta === "/v1/proyectos")
          return json([
            { codigo: "3", nombre: "OBRA-GENERADA", version_vigente: 1, actualizado: null },
            { codigo: "4", nombre: "OBRA-GENERADA", version_vigente: 1, actualizado: null },
            { codigo: "5", nombre: "Galpón", version_vigente: 1, actualizado: null },
          ]);
        return json({ detalle: "No encontrado." }, 404);
      });
      montar();
      const selector = await screen.findByRole("combobox", { name: "Proyecto" });
      await waitFor(() => expect(within(selector).getAllByRole("option")).toHaveLength(4));
      expect(within(selector).getAllByRole("option").map((o) => o.textContent)).toEqual([
        "Sin proyecto",
        "OBRA-GENERADA (3)",
        "OBRA-GENERADA (4)",
        "Galpón",
      ]);
    });

    // VB-9: sin `leer_proyecto` la API contesta 403; no se pide.
    test("una cuenta sin la acción leer_proyecto no pide la lista de proyectos", async () => {
      montar(sesionCon({ acciones: ["administrar_cuentas", "cambiar_caso"] }), "/acerca");
      await screen.findByRole("combobox", { name: "Caso" });
      expect(fetchFalso.mock.calls.some((c) => String(c[0]) === "/v1/proyectos")).toBe(false);
      expect(screen.queryByRole("combobox", { name: "Proyecto" })).not.toBeInTheDocument();
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
    const DOS: PaginaDef[] = [
      { id: "origen", titulo: "Origen de prueba", seccion: "Trabajo", accion: null, cargar: async () => ({ default: Origen }) },
      { id: "destino", titulo: "Destino de prueba", seccion: "Trabajo", accion: null, cargar: async () => ({ default: Destino }) },
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

    test("un enlace del menú conserva el foco: solo se mueve si se perdió", async () => {
      const usuario = userEvent.setup();
      montarDos();
      await screen.findByRole("heading", { name: "Pantalla de origen" });
      const enlace = within(menu()).getByRole("link", { name: "Destino de prueba" });
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

    // Ronda 1 del arbitro: la entrada real es «/» (o una ruta que no existe) y ambas REDIRIGEN con `replace` a la primera
    // pagina; eso es la carga inicial, no un cambio de pagina: el foco sigue en <body> y el primer Tab es «Saltar».
    test.each(["/", "/ruta-inexistente"])("al cargar en %s (redirige a la primera página) no roba el foco", async (entrada) => {
      const usuario = userEvent.setup();
      render(
        <MemoryRouter initialEntries={[entrada]}>
          <Shell sesion={sesionCon()} alSalir={alSalir} alExpirar={alExpirar} paginas={DOS} />
        </MemoryRouter>,
      );
      await screen.findByRole("heading", { name: "Pantalla de origen" });
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
        { id: "lenta", titulo: "Lenta de prueba", seccion: "Trabajo", accion: null, cargar: async () => ({ default: Lenta }) },
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

    test("«Terminar recorrido» con Enter deja el foco en el primer enlace del menú, no en <body>", async () => {
      const usuario = userEvent.setup();
      montar();
      await screen.findByRole("heading", { name: "Pantalla del tablero" });
      act(() => iniciarRecorrido(RECORRIDO_AUDITAR));
      onTestFinished(() => terminarRecorrido());
      const region = within(menu()).getByRole("region", { name: "Recorrido en curso" });
      within(region).getByRole("button", { name: "Terminar recorrido" }).focus();
      await usuario.keyboard("{Enter}");
      expect(within(menu()).queryByRole("region", { name: "Recorrido en curso" })).not.toBeInTheDocument();
      expect(within(menu()).getAllByRole("link")[0]).toHaveFocus();
    });
  });
});
