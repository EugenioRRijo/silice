import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { MemoryRouter, useLocation, useNavigate, type NavigateFunction } from "react-router";
import { BarraSuperior } from "./BarraSuperior";
import { navegacion } from "./navegacion";
import { MODULOS, PAGINAS } from "./rutas";

// Oraculo escrito a mano (plan de modulos, tarea MOD-1), no leido del codigo bajo prueba.
const TODAS = [...new Set(PAGINAS.flatMap((p) => (p.accion ? [p.accion] : [])))];
const OBRAS = MODULOS.find((m) => m.id === "obras")!;
const ENTRADAS = navegacion("obras", TODAS, false);
const PANTALLAS_DE_OBRAS = ["Hoja de la obra", "Elaborar un presupuesto", "Tablero del proyecto", "Entregar paquete"];
const CERRADO = { abierto: false, visible: false, alternar: () => {} };

// Atras/adelante del navegador sin tocar la pagina (un clic en un boton seria un «clic fuera»).
const historial: { navegar: NavigateFunction | null } = { navegar: null };

function Ubicacion() {
  const navegar = useNavigate();
  useEffect(() => {
    historial.navegar = navegar;
  }, [navegar]);
  return <output data-testid="ruta">{useLocation().pathname}</output>;
}

function pintar(entradas: string[] = ["/obras"], indice = entradas.length - 1) {
  return render(
    <MemoryRouter initialEntries={entradas} initialIndex={indice}>
      <BarraSuperior
        modulo={OBRAS}
        entradas={ENTRADAS}
        derecha={<button type="button">derecha</button>}
        sidebar={CERRADO}
      />
      <main>contenido</main>
      <Ubicacion />
    </MemoryRouter>,
  );
}

const nav = () => screen.getByRole("navigation", { name: "Menú principal" });
const area = (nombre: string) => within(nav()).getByRole("button", { name: nombre });
const panel = (nombre: string) => screen.queryByRole("region", { name: nombre });

afterEach(() => {
  historial.navegar = null;
  delete document.documentElement.dataset.siliceLetra;
  // Quita el ancho de ventana fingido (vuelve el del prototipo de jsdom).
  delete (document.documentElement as unknown as Record<string, unknown>).clientWidth;
  vi.restoreAllMocks();
});

// Con `css: false` los estilos no se aplican en jsdom: se leen como texto.
type ModuloFs = { readFileSync(ruta: string, codificacion: string): string };
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: string): ModuloFs } }).process;
const estilosBarra = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/shell/BarraSuperior.scss`, "utf-8")
  .replaceAll("\r\n", "\n");

describe("estilos de «Sílice»", () => {
  test("usa el estilo de tipo body-compact-01 de Carbon, sin tamaño, interlineado ni espaciado a mano", () => {
    const inicio = estilosBarra.indexOf(".silice-barra .silice-barra__silice {");
    expect(inicio).toBeGreaterThan(-1);
    const bloque = estilosBarra.slice(inicio, estilosBarra.indexOf("\n}\n", inicio));
    expect(bloque).toMatch(/@include type\.type-style\("body-compact-01"\)/);
    expect(bloque).not.toMatch(/font-size:|line-height:|letter-spacing:/);
  });
});

describe("BarraSuperior", () => {
  // Plan de modulos, MOD-2: «Sílice» ya no es un enlace al inicio sino el boton que abre el sidebar de modulos.
  test("«Sílice» es el botón que abre los módulos (no un enlace) y lo de la derecha va en la barra", () => {
    pintar();
    const silice = screen.getByRole("button", { name: "Sílice, abrir los módulos" });
    expect(silice).toHaveAttribute("aria-expanded", "false");
    expect(silice).toHaveTextContent("Sílice");
    expect(screen.queryByRole("link", { name: /Sílice/ })).not.toBeInTheDocument();
    // Ya no esta el boton de menu de Carbon (la capa se retiro).
    expect(screen.queryByRole("button", { name: "Abrir el menú" })).not.toBeInTheDocument();
    expect(screen.getByText("derecha")).toBeInTheDocument();
  });

  test("«Sílice» dice su estado: abrir (oculto), cerrar (en capa) o ir a los módulos (fijado); controla el sidebar visible", () => {
    const { rerender } = render(
      <MemoryRouter>
        <BarraSuperior modulo={OBRAS} entradas={ENTRADAS} derecha={null} sidebar={CERRADO} />
      </MemoryRouter>,
    );
    const boton = screen.getByRole("button", { name: "Sílice, abrir los módulos" });
    expect(boton).not.toHaveAttribute("aria-controls");
    rerender(
      <MemoryRouter>
        <BarraSuperior modulo={OBRAS} entradas={ENTRADAS} derecha={null} sidebar={{ abierto: true, visible: true, alternar: () => {} }} />
      </MemoryRouter>,
    );
    expect(boton).toHaveAccessibleName("Sílice, cerrar los módulos");
    expect(boton).toHaveAttribute("aria-expanded", "true");
    expect(boton).toHaveAttribute("aria-controls", "silice-sidebar");
    rerender(
      <MemoryRouter>
        <BarraSuperior modulo={OBRAS} entradas={ENTRADAS} derecha={null} sidebar={{ abierto: false, visible: true, alternar: () => {} }} />
      </MemoryRouter>,
    );
    expect(boton).toHaveAccessibleName("Sílice, ir a los módulos");
    expect(boton).toHaveAttribute("aria-expanded", "true");
    expect(boton).toHaveAttribute("aria-controls", "silice-sidebar");
  });

  test("junto a «Sílice» se lee el nombre del módulo, como texto (no es enlace) y con el nombre completo en title", () => {
    pintar(["/hoja"]);
    const banner = screen.getByRole("banner");
    const nombre = within(banner).getByText("Presupuestos y obras");
    expect(nombre.closest("a")).toBeNull();
    expect(nombre.closest("button")).toBeNull();
    expect(nombre).toHaveAttribute("title", "Presupuestos y obras");
    expect(within(banner).queryByRole("link", { name: "Presupuestos y obras" })).not.toBeInTheDocument();
    // Va despues de «Sílice» y antes de las areas.
    const silice = screen.getByRole("button", { name: "Sílice, abrir los módulos" });
    expect(silice.compareDocumentPosition(nombre) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(nombre.compareDocumentPosition(nav()) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  test("en /hoja las áreas son Inicio, Obras, Partidas, Mercado, Aprobaciones y Control", () => {
    pintar(["/hoja"]);
    const items = [...nav().querySelectorAll<HTMLElement>(".silice-barra__item > a, .silice-barra__item > button")];
    expect(items.map((e) => e.textContent)).toEqual(["Inicio", "Obras", "Partidas", "Mercado", "Aprobaciones", "Control"]);
  });

  test("con rita en /libros: «Auditoría» y las áreas Inicio, Auditar, Paquetes e Historial", () => {
    const auditoria = MODULOS.find((m) => m.id === "auditoria")!;
    render(
      <MemoryRouter initialEntries={["/libros"]}>
        <BarraSuperior
          modulo={auditoria}
          entradas={navegacion("auditoria", ["leer_proyecto", "revisar_paquete", "aprobar_version"], false)}
          derecha={null}
          sidebar={CERRADO}
        />
      </MemoryRouter>,
    );
    expect(within(screen.getByRole("banner")).getByText("Auditoría")).toBeInTheDocument();
    const enlaces = within(nav()).getAllByRole("link");
    expect(enlaces.map((a) => a.textContent)).toEqual(["Inicio", "Auditar", "Paquetes", "Historial"]);
    expect(enlaces.map((a) => a.getAttribute("href"))).toEqual(["/auditoria", "/libros", "/revisar", "/historial"]);
    expect(within(nav()).getByRole("link", { name: "Auditar" })).toHaveAttribute("aria-current", "page");
    expect(within(nav()).queryAllByRole("button")).toHaveLength(0);
  });

  test("sin módulo (ninguno visible) no hay nombre de módulo", () => {
    render(
      <MemoryRouter>
        <BarraSuperior modulo={null} entradas={[]} derecha={null} sidebar={CERRADO} />
      </MemoryRouter>,
    );
    expect(document.querySelector(".silice-barra__modulo")).toBeNull();
  });

  test("un área de una sola pantalla es un enlace; un área con varias es un botón cerrado con aria-controls", () => {
    pintar();
    expect(within(nav()).getByRole("link", { name: "Inicio" })).toHaveAttribute("href", "/obras");
    for (const nombre of ["Obras", "Partidas", "Mercado", "Control"]) {
      const boton = area(nombre);
      expect(boton).toHaveAttribute("aria-expanded", "false");
      expect(boton.getAttribute("aria-controls")).toBeTruthy();
    }
    expect(within(nav()).queryAllByRole("button")).toHaveLength(4);
  });

  test("clic en «Obras» abre su panel con cada pantalla y su línea; el foco va al primer enlace", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Obras"));
    expect(area("Obras")).toHaveAttribute("aria-expanded", "true");
    const region = panel("Obras")!;
    expect(region).toBeInTheDocument();
    expect(region.id).toBe(area("Obras").getAttribute("aria-controls"));
    const enlaces = within(region).getAllByRole("link");
    expect(enlaces.map((e) => e.getAttribute("href"))).toEqual(["/hoja", "/elaborar", "/tablero", "/entregar"]);
    for (const titulo of PANTALLAS_DE_OBRAS) expect(within(region).getByRole("link", { name: titulo })).toBeInTheDocument();
    const hoja = within(region).getByRole("link", { name: "Hoja de la obra" });
    expect(hoja).toHaveAccessibleDescription("El presupuesto completo, como en Excel");
    expect(within(region).getByText("El presupuesto completo, como en Excel")).toBeVisible();
    expect(within(region).getByText("Junte partidas y cantidades")).toBeVisible();
    expect(hoja).toHaveFocus();
  });

  test("Intro sobre «Obras» abre igual; Esc cierra y el foco vuelve al botón", async () => {
    const u = userEvent.setup();
    pintar();
    area("Obras").focus();
    await u.keyboard("{Enter}");
    expect(panel("Obras")).toBeInTheDocument();
    expect(within(panel("Obras")!).getByRole("link", { name: "Hoja de la obra" })).toHaveFocus();
    await u.keyboard("{Escape}");
    expect(panel("Obras")).toBeNull();
    expect(area("Obras")).toHaveAttribute("aria-expanded", "false");
    expect(area("Obras")).toHaveFocus();
  });

  test("las flechas recorren las entradas del panel y se detienen en la primera y la última (sin vuelta)", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Obras"));
    await u.keyboard("{ArrowDown}");
    expect(screen.getByRole("link", { name: "Elaborar un presupuesto" })).toHaveFocus();
    await u.keyboard("{ArrowUp}{ArrowUp}");
    expect(screen.getByRole("link", { name: "Hoja de la obra" })).toHaveFocus();
    await u.keyboard("{End}");
    expect(screen.getByRole("link", { name: "Entregar paquete" })).toHaveFocus();
    await u.keyboard("{ArrowDown}");
    expect(screen.getByRole("link", { name: "Entregar paquete" })).toHaveFocus();
    await u.keyboard("{Home}");
    expect(screen.getByRole("link", { name: "Hoja de la obra" })).toHaveFocus();
  });

  test("Espacio sobre el botón del área abre el panel", async () => {
    const u = userEvent.setup();
    pintar();
    area("Partidas").focus();
    await u.keyboard(" ");
    expect(area("Partidas")).toHaveAttribute("aria-expanded", "true");
    expect(panel("Partidas")).toBeInTheDocument();
  });

  test("Tab desde el último enlace del panel va a la siguiente área (el foco sigue en la navegación)", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Obras"));
    await u.keyboard("{End}");
    expect(screen.getByRole("link", { name: "Entregar paquete" })).toHaveFocus();
    await u.tab();
    expect(area("Partidas")).toHaveFocus();
  });

  test("clic en una zona del panel que no es enlace no lo cierra y el foco queda dentro de la navegación", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Mercado"));
    const region = panel("Mercado")!;
    await u.click(region);
    expect(panel("Mercado")).toBeInTheDocument();
    expect(area("Mercado")).toHaveAttribute("aria-expanded", "true");
    expect(nav()).toContainElement(document.activeElement as HTMLElement);
    // Y las flechas siguen sirviendo desde ahí.
    await u.keyboard("{ArrowDown}");
    expect(screen.getByRole("link", { name: "Estudio de mercado" })).toHaveFocus();
  });

  test("el segundo clic sobre el área abierta la cierra una sola vez aunque el botón no tome el foco (Safari)", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Obras"));
    const enlace = screen.getByRole("link", { name: "Hoja de la obra" });
    expect(enlace).toHaveFocus();
    // Safari: al apretar el botón, este no toma el foco; el enlace lo pierde hacia el body (relatedTarget nulo).
    const boton = area("Obras");
    fireEvent.mouseDown(boton);
    act(() => enlace.blur());
    fireEvent.mouseUp(boton);
    fireEvent.click(boton);
    expect(panel("Obras")).toBeNull();
    expect(area("Obras")).toHaveAttribute("aria-expanded", "false");
  });

  test("Tab que saca el foco de la navegación cierra el panel", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Control"));
    await u.keyboard("{End}");
    expect(screen.getByRole("link", { name: "Escenarios de sensibilidad" })).toHaveFocus();
    await u.tab();
    expect(screen.getByRole("button", { name: "derecha" })).toHaveFocus();
    expect(panel("Control")).toBeNull();
    expect(area("Control")).toHaveAttribute("aria-expanded", "false");
  });

  test("al redimensionar la ventana el panel abierto se vuelve a encajar en el ancho útil (sin la barra de desplazamiento)", async () => {
    const u = userEvent.setup();
    let ancho = 1000;
    Object.defineProperty(document.documentElement, "clientWidth", { configurable: true, get: () => ancho });
    const original = HTMLElement.prototype.getBoundingClientRect;
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function (this: HTMLElement) {
      // El panel mide de 500 a 900 px, sea cual sea el desplazamiento puesto.
      return this.classList.contains("silice-panel-area") ? new DOMRect(500, 48, 400, 300) : original.call(this);
    });
    pintar();
    await u.click(area("Control"));
    const region = panel("Control")!;
    expect(region.style.insetInlineStart).toBe("");
    expect(region.style.maxInlineSize).toBe("min(40rem, 984px)");
    ancho = 800;
    act(() => {
      window.dispatchEvent(new Event("resize"));
    });
    // 900 - (800 - 8) = 108 px de exceso.
    expect(region.style.insetInlineStart).toBe("-108px");
    expect(region.style.maxInlineSize).toBe("min(40rem, 784px)");
    ancho = 1000;
    act(() => {
      window.dispatchEvent(new Event("resize"));
    });
    expect(region.style.insetInlineStart).toBe("");
  });

  test("clic fuera (en el main) cierra; abrir «Control» cierra «Obras»", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Obras"));
    await u.click(screen.getByRole("main"));
    expect(panel("Obras")).toBeNull();
    await u.click(area("Obras"));
    await u.click(area("Control"));
    expect(panel("Obras")).toBeNull();
    expect(area("Obras")).toHaveAttribute("aria-expanded", "false");
    expect(panel("Control")).toBeInTheDocument();
    expect(screen.getAllByRole("region")).toHaveLength(1);
  });

  test("con el teclado, abrir otra área también deja un solo panel", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Obras"));
    area("Partidas").focus();
    await u.keyboard("{Enter}");
    expect(panel("Obras")).toBeNull();
    expect(panel("Partidas")).toBeInTheDocument();
  });

  test("cada panel es una sola lista, sin subtítulos, con las pantallas en el orden del registro", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Mercado"));
    const region = panel("Mercado")!;
    expect(within(region).getAllByRole("list")).toHaveLength(1);
    expect(region.querySelector(".silice-panel-area__subtitulo")).toBeNull();
    expect(within(region).getAllByRole("link").map((e) => e.getAttribute("href"))).toEqual([
      "/mercado",
      "/precios_empresa",
      "/actualizacion",
      "/historico",
      "/indices",
      "/simulador",
    ]);
  });

  test("elegir «Componer una partida» navega a /componer y cierra el panel", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Partidas"));
    await u.click(screen.getByRole("link", { name: "Componer una partida" }));
    expect(screen.getByTestId("ruta")).toHaveTextContent("/componer");
    expect(panel("Partidas")).toBeNull();
    expect(area("Partidas")).toHaveAttribute("aria-expanded", "false");
  });

  test("en /componer «Partidas» lleva la marca de actual y la pantalla del panel aria-current", async () => {
    const u = userEvent.setup();
    pintar(["/componer"]);
    expect(area("Partidas")).toHaveClass("silice-barra__area--actual");
    expect(area("Obras")).not.toHaveClass("silice-barra__area--actual");
    expect(within(nav()).getByRole("link", { name: "Inicio" })).not.toHaveAttribute("aria-current");
    await u.click(area("Partidas"));
    expect(screen.getByRole("link", { name: "Componer una partida" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Catálogo de partidas e insumos" })).not.toHaveAttribute("aria-current");
  });

  test("un área de enlace marca la pantalla actual", () => {
    pintar(["/obras"]);
    expect(within(nav()).getByRole("link", { name: "Inicio" })).toHaveAttribute("aria-current", "page");
  });

  test("foco de revisión 2: atrás del navegador con el panel abierto lo cierra y la marca pasa al área nueva", async () => {
    const u = userEvent.setup();
    pintar(["/hoja", "/componer"]);
    expect(area("Partidas")).toHaveClass("silice-barra__area--actual");
    await u.click(area("Partidas"));
    expect(panel("Partidas")).toBeInTheDocument();
    act(() => historial.navegar!(-1));
    expect(screen.getByTestId("ruta")).toHaveTextContent("/hoja");
    expect(panel("Partidas")).toBeNull();
    expect(area("Partidas")).toHaveAttribute("aria-expanded", "false");
    expect(area("Partidas")).not.toHaveClass("silice-barra__area--actual");
    expect(area("Obras")).toHaveClass("silice-barra__area--actual");
    // Y al volver adelante el panel no reaparece solo.
    act(() => historial.navegar!(1));
    expect(panel("Partidas")).toBeNull();
  });

  test("foco de revisión 3: cambiar el tamaño de letra con un panel abierto lo cierra", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Obras"));
    expect(panel("Obras")).toBeInTheDocument();
    act(() => {
      document.documentElement.dataset.siliceLetra = "grande";
    });
    await waitFor(() => expect(panel("Obras")).toBeNull());
    expect(area("Obras")).toHaveAttribute("aria-expanded", "false");
  });

  test("pasar el ratón por encima no abre nada", async () => {
    const u = userEvent.setup();
    pintar();
    for (const nombre of ["Obras", "Partidas", "Mercado", "Control"]) await u.hover(area(nombre));
    expect(screen.queryAllByRole("region")).toHaveLength(0);
    for (const nombre of ["Obras", "Partidas", "Mercado", "Control"]) expect(area(nombre)).toHaveAttribute("aria-expanded", "false");
  });

  test("el panel es navegación con enlaces, no un menú", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Mercado"));
    expect(screen.queryAllByRole("menu")).toHaveLength(0);
    expect(screen.queryAllByRole("menuitem")).toHaveLength(0);
    expect(nav()).toContainElement(panel("Mercado"));
  });

  test("clic en «Sílice» llama a alternar y cierra el panel de área abierto", async () => {
    const u = userEvent.setup();
    let veces = 0;
    render(
      <MemoryRouter>
        <BarraSuperior
          modulo={OBRAS}
          entradas={ENTRADAS}
          derecha={null}
          sidebar={{ abierto: false, visible: false, alternar: () => (veces += 1) }}
        />
      </MemoryRouter>,
    );
    await u.click(area("Obras"));
    expect(panel("Obras")).toBeInTheDocument();
    await u.click(screen.getByRole("button", { name: "Sílice, abrir los módulos" }));
    expect(veces).toBe(1);
    expect(panel("Obras")).toBeNull();
  });

  test("sin entradas la barra no pinta áreas ni falla", () => {
    render(
      <MemoryRouter>
        <BarraSuperior modulo={OBRAS} entradas={[]} derecha={null} sidebar={CERRADO} />
      </MemoryRouter>,
    );
    const menu = screen.getByRole("navigation", { name: "Menú principal" });
    expect(within(menu).queryAllByRole("link")).toHaveLength(0);
    expect(within(menu).queryAllByRole("button")).toHaveLength(0);
  });
});
