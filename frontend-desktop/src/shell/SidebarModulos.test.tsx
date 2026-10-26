import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { MemoryRouter, useLocation } from "react-router";
import { afterEach, describe, expect, test, vi } from "vitest";
import { navegacion } from "./navegacion";
import { fueraDeModulos, modulosVisibles } from "./rutas";
import { abrirSidebar, estadoSidebar, iniciarSidebar } from "./sidebar";
import { SidebarModulos } from "./SidebarModulos";

// Acciones de ana (arma) y del administrador, escritas a mano desde PERMISOS de seguridad/permisos.py.
const ANA = [
  "editar_hoja",
  "convertir_y_reajustar",
  "control_de_obra",
  "decidir_recuperacion",
  "entregar_paquete",
  "operar_arenera",
  "leer_proyecto",
  "cambiar_caso",
];
const ADMIN = [
  "operar_arenera",
  "cambiar_caso",
  "administrar_cuentas",
  "administrar_empresa",
  "administrar_precios",
  "administrar_red_y_api",
  "cambiar_carpeta_de_datos",
];

type Props = ComponentProps<typeof SidebarModulos>;

function Ruta() {
  return <output data-testid="ruta">{useLocation().pathname}</output>;
}

function pintar(parcial: Partial<Props> = {}, ruta = "/hoja", acciones = ANA) {
  const alCerrar = vi.fn();
  const alFijar = vi.fn();
  const props: Props = {
    modulos: modulosVisibles(acciones, false),
    actual: "obras",
    entradas: navegacion("obras", acciones, false),
    fuera: fueraDeModulos(acciones, false),
    abierto: true,
    fijado: false,
    fijadoPosible: false,
    alCerrar,
    alFijar,
    nombre: "Ana Pérez",
    ...parcial,
  };
  const r = render(
    <MemoryRouter initialEntries={[ruta]}>
      <button type="button">antes</button>
      <SidebarModulos {...props} />
      <Ruta />
    </MemoryRouter>,
  );
  return { ...r, alCerrar, alFijar };
}

const enCapa = () => screen.getByRole("dialog", { name: "Módulos de Sílice" });
const modulo = (nombre: string) => screen.getByRole("link", { name: nombre });

afterEach(() => iniciarSidebar(false));

describe("SidebarModulos", () => {
  test("oculto (ni abierto ni fijado) no pinta nada", () => {
    const { container } = pintar({ abierto: false });
    expect(container.querySelector(".silice-sidebar")).toBeNull();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });

  test("fijado pero sin ancho para fijarlo, y sin abrir, tampoco se pinta", () => {
    pintar({ abierto: false, fijado: true, fijadoPosible: false });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation")).not.toBeInTheDocument();
  });

  test("abierto es un diálogo modal «Módulos de Sílice» con su capa", () => {
    const { container } = pintar();
    const caja = enCapa();
    expect(caja).toHaveAttribute("aria-modal", "true");
    expect(caja.id).toBe("silice-sidebar");
    expect(container.querySelector(".silice-sidebar__fondo")).not.toBeNull();
    expect(within(caja).getByText("Módulos")).toBeInTheDocument();
  });

  test("un renglón por módulo, en orden, con su línea de qué hace; el actual con aria-current y el foco", () => {
    pintar();
    const lista = enCapa().querySelector(".silice-sidebar__modulos")!;
    const enlaces = within(lista as HTMLElement).getAllByRole("link");
    expect(enlaces.map((a) => a.getAttribute("href"))).toEqual(["/auditoria", "/obras", "/produccion"]);
    expect(modulo("Auditoría")).toHaveAccessibleDescription("Revise presupuestos propios o de terceros");
    expect(modulo("Presupuestos y obras")).toHaveAccessibleDescription("Arme, apruebe y controle sus obras");
    expect(modulo("Producción")).toHaveAccessibleDescription("Existencias y báscula de la arenera");
    expect(modulo("Presupuestos y obras")).toHaveAttribute("aria-current", "page");
    expect(modulo("Auditoría")).not.toHaveAttribute("aria-current");
    expect(modulo("Presupuestos y obras")).toHaveFocus();
    // Nombre en heading-03 y la línea en helper-text (DESIGN.md), sin ser encabezados.
    expect(modulo("Presupuestos y obras").querySelector(".cds--type-heading-03")?.textContent).toBe("Presupuestos y obras");
    expect(modulo("Presupuestos y obras").querySelector(".cds--type-helper-text-01")?.textContent).toBe(
      "Arme, apruebe y controle sus obras",
    );
    expect(within(enCapa()).queryAllByRole("heading")).toHaveLength(0);
  });

  test("las áreas del módulo abierto: cada pantalla una vez, con su línea; las de una sola pantalla sin rótulo repetido", () => {
    pintar();
    const areas = enCapa().querySelector<HTMLElement>(".silice-sidebar__areas")!;
    expect(within(areas).getByText("Áreas de Presupuestos y obras")).toBeInTheDocument();
    const hrefs = within(areas)
      .getAllByRole("link")
      .map((a) => a.getAttribute("href"));
    // Oráculo a mano: lo mismo que la barra de ana en Presupuestos y obras (plan de módulos, MOD-1).
    expect(hrefs).toEqual([
      "/obras",
      "/hoja",
      "/elaborar",
      "/tablero",
      "/entregar",
      "/componer",
      "/catalogo",
      "/similares",
      "/actualizacion",
      "/historico",
      "/simulador",
      "/control",
      "/reajuste",
      "/escenarios",
    ]);
    expect(within(areas).getByRole("link", { name: "Hoja del proyecto" })).toHaveAccessibleDescription(
      "El presupuesto completo, como en Excel",
    );
    expect(within(areas).getByRole("link", { name: "Hoja del proyecto" })).toHaveAttribute("aria-current", "page");
    const rotulos = [...areas.querySelectorAll(".silice-sidebar__rotulo-area")].map((p) => p.textContent);
    expect(rotulos).toEqual(["Obras", "Partidas", "Mercado", "Control"]);
  });

  test("al pie: Acerca de Sílice (ana no administra), la sesión y nada de Administración", () => {
    pintar();
    const pie = enCapa().querySelector<HTMLElement>(".silice-sidebar__pie")!;
    expect(within(pie).getByRole("link", { name: "Acerca de Sílice" })).toHaveAttribute("href", "/acerca");
    expect(within(pie).queryByRole("link", { name: "Administración" })).not.toBeInTheDocument();
    expect(within(pie).getByText("Sesión de Ana Pérez")).toBeInTheDocument();
  });

  test("con el administrador el pie trae Administración y Acerca de Sílice", () => {
    pintar(
      {
        modulos: modulosVisibles(ADMIN, false),
        entradas: navegacion("obras", ADMIN, false),
        fuera: fueraDeModulos(ADMIN, false),
        nombre: "Admin",
      },
      "/precios_empresa",
      ADMIN,
    );
    const pie = enCapa().querySelector<HTMLElement>(".silice-sidebar__pie")!;
    expect(within(pie).getAllByRole("link").map((a) => a.textContent)).toEqual(["Administración", "Acerca de Sílice"]);
    const lista = enCapa().querySelector<HTMLElement>(".silice-sidebar__modulos")!;
    expect(within(lista).getAllByRole("link").map((a) => a.getAttribute("href"))).toEqual(["/obras", "/produccion"]);
  });

  test("en capa, «Fijar» solo si hay ancho para fijarlo; llama alFijar(true)", async () => {
    const { alFijar, unmount } = pintar({ fijadoPosible: false });
    expect(within(enCapa()).queryByRole("button", { name: "Fijar" })).not.toBeInTheDocument();
    expect(within(enCapa()).queryByRole("button", { name: "Ocultar" })).not.toBeInTheDocument();
    unmount();
    const otro = pintar({ fijadoPosible: true });
    await userEvent.click(within(enCapa()).getByRole("button", { name: "Fijar" }));
    expect(otro.alFijar).toHaveBeenCalledWith(true);
    expect(alFijar).not.toHaveBeenCalled();
  });

  test("fijado y con ancho: navegación «Módulos» sin capa ni diálogo, con «Ocultar»", async () => {
    const { container, alFijar } = pintar({ abierto: false, fijado: true, fijadoPosible: true });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    const nav = screen.getByRole("navigation", { name: "Módulos" });
    expect(nav.id).toBe("silice-sidebar");
    expect(container.querySelector(".silice-sidebar__fondo")).toBeNull();
    expect(within(nav).queryByRole("button", { name: "Fijar" })).not.toBeInTheDocument();
    // Fijado no le roba el foco a la página al pintarse.
    expect(modulo("Presupuestos y obras")).not.toHaveFocus();
    await userEvent.click(within(nav).getByRole("button", { name: "Ocultar" }));
    expect(alFijar).toHaveBeenCalledWith(false);
  });

  test("fijado sin ancho para fijarlo, al abrirse sale en capa y sin «Fijar» ni «Ocultar»", () => {
    pintar({ abierto: true, fijado: true, fijadoPosible: false });
    expect(enCapa()).toBeInTheDocument();
    expect(within(enCapa()).queryByRole("button")).not.toBeInTheDocument();
  });

  test("Esc dentro de la capa llama alCerrar", async () => {
    const { alCerrar } = pintar();
    await userEvent.keyboard("{Escape}");
    expect(alCerrar).toHaveBeenCalledTimes(1);
  });

  test("clic en la capa (fuera del sidebar) llama alCerrar", async () => {
    const { container, alCerrar } = pintar();
    await userEvent.click(container.querySelector<HTMLElement>(".silice-sidebar__fondo")!);
    expect(alCerrar).toHaveBeenCalledTimes(1);
  });

  test("foco atrapado en la capa: Tab desde el último vuelve al primero y Mayús+Tab desde el primero va al último", async () => {
    const u = userEvent.setup();
    pintar({ fijadoPosible: true });
    const primero = modulo("Auditoría");
    const ultimo = within(enCapa()).getByRole("button", { name: "Fijar" });
    ultimo.focus();
    await u.tab();
    expect(primero).toHaveFocus();
    await u.tab({ shift: true });
    expect(ultimo).toHaveFocus();
  });

  test("elegir un módulo navega a su inicio y cierra el sidebar", async () => {
    abrirSidebar();
    pintar();
    await userEvent.click(modulo("Auditoría"));
    expect(screen.getByTestId("ruta").textContent).toBe("/auditoria");
    expect(estadoSidebar().abierto).toBe(false);
  });

  test("elegir una pantalla de un área o del pie tambien cierra el sidebar", async () => {
    abrirSidebar();
    pintar();
    await userEvent.click(screen.getByRole("link", { name: "Componer una partida" }));
    expect(screen.getByTestId("ruta").textContent).toBe("/componer");
    expect(estadoSidebar().abierto).toBe(false);
  });
});

// Con `css: false` los estilos no se aplican en jsdom: se leen como texto (como estilosLetra.test.ts).
type ModuloFs = { readFileSync(ruta: string, codificacion: string): string };
const nodo = (globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: string): ModuloFs } }).process;
const estilos = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/shell/SidebarModulos.scss`, "utf-8");

describe("estilos del sidebar (DESIGN.md y plan de módulos)", () => {
  test("superficie oscura de Carbon con texto inverso y la marca del módulo actual en azul inverso (≥ 3:1)", () => {
    expect(estilos).toMatch(/\.silice-sidebar\s*\{[^}]*background:\s*var\(--cds-background-inverse\)/);
    expect(estilos).toMatch(/\.silice-sidebar\s*\{[^}]*color:\s*var\(--cds-text-inverse\)/);
    expect(estilos).toMatch(/\[aria-current="page"\][^{]*\{[^}]*border-inline-start-color:\s*var\(--cds-link-inverse\)/);
    expect(estilos).toMatch(/:focus-visible\s*\{[^}]*outline:\s*2px solid var\(--cds-focus-inverse\)/);
  });

  test("264 px que siguen la letra, fijado empuja el contenido y la capa usa $overlay", () => {
    expect(estilos).toMatch(/calc\(264px \* var\(--silice-escala-letra\)\)/);
    expect(estilos).toMatch(
      /\.silice-marco--fijado \.silice-contenido\s*\{\s*margin-inline-start:\s*calc\(264px \* var\(--silice-escala-letra\)\)/,
    );
    expect(estilos).toMatch(/\.silice-sidebar__fondo\s*\{[^}]*background:\s*var\(--cds-overlay\)/);
  });

  test("las áreas solo se ven por debajo del umbral del módulo (las muestra shell.scss)", () => {
    expect(estilos).toMatch(/\.silice-sidebar__areas\s*\{\s*display:\s*none/);
  });

  test("sin animación, sin sombras, sin esquinas redondeadas", () => {
    expect(estilos).not.toMatch(/transition:(?!\s*none)/);
    expect(estilos).not.toMatch(/animation/);
    expect(estilos).not.toMatch(/box-shadow/);
    expect(estilos).not.toMatch(/border-radius/);
  });
});
