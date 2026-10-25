import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { afterEach, describe, expect, test } from "vitest";
import { MemoryRouter, useLocation, useNavigate, type NavigateFunction } from "react-router";
import { BarraSuperior } from "./BarraSuperior";
import { navegacion } from "./navegacion";
import { PAGINAS } from "./rutas";

// Oraculo escrito a mano (AREAS de rutas.ts y la maqueta aprobada), no leido del codigo bajo prueba.
const TODAS = [...new Set(PAGINAS.flatMap((p) => (p.accion ? [p.accion] : [])))];
const ENTRADAS = navegacion(TODAS, false);
const PAGINAS_DE_CREAR = [
  "Componer una partida",
  "Elaborar un presupuesto",
  "Hoja del proyecto",
  "Catálogo de partidas e insumos",
  "Tablero del proyecto",
  "Entregar paquete",
];

// Atras/adelante del navegador sin tocar la pagina (un clic en un boton seria un «clic fuera»).
const historial: { navegar: NavigateFunction | null } = { navegar: null };

function Ubicacion() {
  const navegar = useNavigate();
  useEffect(() => {
    historial.navegar = navegar;
  }, [navegar]);
  return <output data-testid="ruta">{useLocation().pathname}</output>;
}

function pintar(entradas: string[] = ["/inicio"], indice = entradas.length - 1) {
  return render(
    <MemoryRouter initialEntries={entradas} initialIndex={indice}>
      <BarraSuperior
        entradas={ENTRADAS}
        derecha={<span>derecha</span>}
        menu={{ abierto: false, alternar: () => {} }}
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
});

describe("BarraSuperior", () => {
  test("Sílice lleva a Inicio y lo de la derecha va en la barra", () => {
    pintar();
    expect(screen.getByRole("link", { name: "Sílice" })).toHaveAttribute("href", "#/");
    expect(screen.getByText("derecha")).toBeInTheDocument();
  });

  test("un área de una sola pantalla es un enlace; un área con varias es un botón cerrado con aria-controls", () => {
    pintar();
    expect(within(nav()).getByRole("link", { name: "Inicio" })).toHaveAttribute("href", "/inicio");
    expect(within(nav()).getByRole("link", { name: "Existencias de la arenera" })).toHaveAttribute("href", "/existencias");
    for (const nombre of ["Auditar", "Crear", "Más"]) {
      const boton = area(nombre);
      expect(boton).toHaveAttribute("aria-expanded", "false");
      expect(boton.getAttribute("aria-controls")).toBeTruthy();
    }
    expect(within(nav()).queryAllByRole("button")).toHaveLength(3);
  });

  test("clic en «Crear» abre su panel con cada pantalla y su línea; el foco va al primer enlace", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Crear"));
    expect(area("Crear")).toHaveAttribute("aria-expanded", "true");
    const region = panel("Crear")!;
    expect(region).toBeInTheDocument();
    expect(region.id).toBe(area("Crear").getAttribute("aria-controls"));
    const enlaces = within(region).getAllByRole("link");
    expect(enlaces.map((e) => e.getAttribute("href"))).toEqual([
      "/componer",
      "/elaborar",
      "/hoja",
      "/catalogo",
      "/tablero",
      "/entregar",
    ]);
    for (const titulo of PAGINAS_DE_CREAR) expect(within(region).getByRole("link", { name: titulo })).toBeInTheDocument();
    const componer = within(region).getByRole("link", { name: "Componer una partida" });
    expect(componer).toHaveAccessibleDescription("Arme el análisis de precio de una partida");
    expect(within(region).getByText("Arme el análisis de precio de una partida")).toBeVisible();
    expect(within(region).getByText("Junte partidas y cantidades")).toBeVisible();
    expect(componer).toHaveFocus();
  });

  test("Intro sobre «Crear» abre igual; Esc cierra y el foco vuelve al botón", async () => {
    const u = userEvent.setup();
    pintar();
    area("Crear").focus();
    await u.keyboard("{Enter}");
    expect(panel("Crear")).toBeInTheDocument();
    expect(within(panel("Crear")!).getByRole("link", { name: "Componer una partida" })).toHaveFocus();
    await u.keyboard("{Escape}");
    expect(panel("Crear")).toBeNull();
    expect(area("Crear")).toHaveAttribute("aria-expanded", "false");
    expect(area("Crear")).toHaveFocus();
  });

  test("las flechas recorren las entradas del panel", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Crear"));
    await u.keyboard("{ArrowDown}");
    expect(screen.getByRole("link", { name: "Elaborar un presupuesto" })).toHaveFocus();
    await u.keyboard("{ArrowUp}{ArrowUp}");
    expect(screen.getByRole("link", { name: "Entregar paquete" })).toHaveFocus();
    await u.keyboard("{Home}");
    expect(screen.getByRole("link", { name: "Componer una partida" })).toHaveFocus();
  });

  test("clic fuera (en el main) cierra; abrir «Más» cierra «Crear»", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Crear"));
    await u.click(screen.getByRole("main"));
    expect(panel("Crear")).toBeNull();
    await u.click(area("Crear"));
    await u.click(area("Más"));
    expect(panel("Crear")).toBeNull();
    expect(area("Crear")).toHaveAttribute("aria-expanded", "false");
    expect(panel("Más")).toBeInTheDocument();
    expect(screen.getAllByRole("region")).toHaveLength(1);
  });

  test("con el teclado, abrir otra área también deja un solo panel", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Crear"));
    area("Auditar").focus();
    await u.keyboard("{Enter}");
    expect(panel("Crear")).toBeNull();
    expect(panel("Auditar")).toBeInTheDocument();
  });

  test("«Más» muestra los subtítulos Precios, Obra, Análisis y Ajustes, cada uno con sus pantallas", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Más"));
    const region = panel("Más")!;
    expect(within(region).getAllByRole("list")).toHaveLength(4);
    const obra = within(region).getByRole("list", { name: "Obra" });
    expect(within(obra).getAllByRole("link").map((e) => e.getAttribute("href"))).toEqual(["/control"]);
    const ajustes = within(region).getByRole("list", { name: "Ajustes" });
    expect(within(ajustes).getAllByRole("link").map((e) => e.getAttribute("href"))).toEqual(["/administracion", "/acerca"]);
    for (const t of ["Precios", "Obra", "Análisis", "Ajustes"]) expect(within(region).getByText(t)).toBeVisible();
  });

  test("elegir «Componer una partida» navega a /componer y cierra el panel", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Crear"));
    await u.click(screen.getByRole("link", { name: "Componer una partida" }));
    expect(screen.getByTestId("ruta")).toHaveTextContent("/componer");
    expect(panel("Crear")).toBeNull();
    expect(area("Crear")).toHaveAttribute("aria-expanded", "false");
  });

  test("en /componer «Crear» lleva la marca de actual y la pantalla del panel aria-current", async () => {
    const u = userEvent.setup();
    pintar(["/componer"]);
    expect(area("Crear")).toHaveClass("silice-barra__area--actual");
    expect(area("Auditar")).not.toHaveClass("silice-barra__area--actual");
    expect(within(nav()).getByRole("link", { name: "Inicio" })).not.toHaveAttribute("aria-current");
    await u.click(area("Crear"));
    expect(screen.getByRole("link", { name: "Componer una partida" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Hoja del proyecto" })).not.toHaveAttribute("aria-current");
  });

  test("un área de enlace marca la pantalla actual", () => {
    pintar(["/inicio"]);
    expect(within(nav()).getByRole("link", { name: "Inicio" })).toHaveAttribute("aria-current", "page");
  });

  test("foco de revisión 2: atrás del navegador con el panel abierto lo cierra y la marca pasa al área nueva", async () => {
    const u = userEvent.setup();
    pintar(["/libros", "/componer"]);
    expect(area("Crear")).toHaveClass("silice-barra__area--actual");
    await u.click(area("Crear"));
    expect(panel("Crear")).toBeInTheDocument();
    act(() => historial.navegar!(-1));
    expect(screen.getByTestId("ruta")).toHaveTextContent("/libros");
    expect(panel("Crear")).toBeNull();
    expect(area("Crear")).toHaveAttribute("aria-expanded", "false");
    expect(area("Crear")).not.toHaveClass("silice-barra__area--actual");
    expect(area("Auditar")).toHaveClass("silice-barra__area--actual");
    // Y al volver adelante el panel no reaparece solo.
    act(() => historial.navegar!(1));
    expect(panel("Crear")).toBeNull();
  });

  test("foco de revisión 3: cambiar el tamaño de letra con un panel abierto lo cierra", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Crear"));
    expect(panel("Crear")).toBeInTheDocument();
    act(() => {
      document.documentElement.dataset.siliceLetra = "grande";
    });
    await waitFor(() => expect(panel("Crear")).toBeNull());
    expect(area("Crear")).toHaveAttribute("aria-expanded", "false");
  });

  test("pasar el ratón por encima no abre nada", async () => {
    const u = userEvent.setup();
    pintar();
    for (const nombre of ["Auditar", "Crear", "Más"]) await u.hover(area(nombre));
    expect(screen.queryAllByRole("region")).toHaveLength(0);
    for (const nombre of ["Auditar", "Crear", "Más"]) expect(area(nombre)).toHaveAttribute("aria-expanded", "false");
  });

  test("el panel es navegación con enlaces, no un menú", async () => {
    const u = userEvent.setup();
    pintar();
    await u.click(area("Más"));
    expect(screen.queryAllByRole("menu")).toHaveLength(0);
    expect(screen.queryAllByRole("menuitem")).toHaveLength(0);
    expect(nav()).toContainElement(panel("Más"));
  });

  test("el botón del menú en capa refleja su estado y llama a alternar", async () => {
    const u = userEvent.setup();
    let veces = 0;
    render(
      <MemoryRouter>
        <BarraSuperior entradas={ENTRADAS} derecha={null} menu={{ abierto: false, alternar: () => (veces += 1) }} />
      </MemoryRouter>,
    );
    const boton = screen.getByRole("button", { name: "Abrir el menú" });
    expect(boton).toHaveAttribute("aria-expanded", "false");
    await u.click(boton);
    expect(veces).toBe(1);
  });

  test("sin entradas la barra no pinta áreas ni falla", () => {
    render(
      <MemoryRouter>
        <BarraSuperior entradas={[]} derecha={null} menu={{ abierto: false, alternar: () => {} }} />
      </MemoryRouter>,
    );
    const menu = screen.getByRole("navigation", { name: "Menú principal" });
    expect(within(menu).queryAllByRole("link")).toHaveLength(0);
    expect(within(menu).queryAllByRole("button")).toHaveLength(0);
  });
});
