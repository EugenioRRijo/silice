import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { describe, expect, it } from "vitest";
import { BarraDeEspacio, pestanasUsables } from "./BarraDeEspacio";
import { ESPACIOS, SUBVISTAS, rutaCanonica } from "./espacios";

// Con `css: false` el `?raw` de un .scss llega vacío: el fuente se lee con el módulo de Node (como BarraLateral.test.tsx).
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }
).process;
const leer = (ruta: string) => nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/${ruta}`, "utf-8");

const PESTANAS = [
  { id: "resumen", titulo: "Resumen", ruta: "/obra/demo.db/1/resumen" },
  { id: "presupuesto", titulo: "Presupuesto", ruta: "/obra/demo.db/1/presupuesto" },
  { id: "tramos", titulo: "Tramos", ruta: "/obra/demo.db/1/tramos" },
];

function pintar(propiedades: Partial<Parameters<typeof BarraDeEspacio>[0]> = {}) {
  return render(
    <MemoryRouter>
      <BarraDeEspacio etiqueta="Secciones de la obra" pestanas={PESTANAS} activa="presupuesto" nivel="espacio" {...propiedades} />
    </MemoryRouter>,
  );
}

const rutaDe = (h: { pagina: string }) => rutaCanonica(h.pagina) ?? "";
const ids = (pestanas: readonly { id: string }[]) => pestanas.map((p) => p.id);

// Plan F6, T3. La barra navega por URL: cada pestaña es un enlace a su ruta, no un panel local (por eso no es un tablist).
describe("BarraDeEspacio: semántica", () => {
  it("es una navegación con el nombre que recibe", () => {
    pintar();
    expect(screen.getByRole("navigation", { name: "Secciones de la obra" })).toBeInTheDocument();
  });

  it("cada pestaña es un enlace con su ruta y su texto", () => {
    pintar();
    const nav = screen.getByRole("navigation", { name: "Secciones de la obra" });
    const enlaces = within(nav).getAllByRole("link");
    expect(enlaces.map((e) => e.textContent)).toEqual(["Resumen", "Presupuesto", "Tramos"]);
    expect(enlaces.map((e) => e.getAttribute("href"))).toEqual([
      "/obra/demo.db/1/resumen",
      "/obra/demo.db/1/presupuesto",
      "/obra/demo.db/1/tramos",
    ]);
  });

  it("solo la activa lleva aria-current=page", () => {
    pintar();
    expect(screen.getByRole("link", { name: "Presupuesto" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Resumen" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("link", { name: "Tramos" })).not.toHaveAttribute("aria-current");
    expect(document.querySelectorAll('[aria-current="page"]')).toHaveLength(1);
  });

  it("no usa roles de pestañas (navega por URL) ni pone un encabezado", () => {
    pintar();
    expect(screen.queryByRole("tablist")).toBeNull();
    expect(screen.queryByRole("tab")).toBeNull();
    expect(document.querySelector("[role='tablist'], [role='tab'], [aria-selected]")).toBeNull();
    expect(screen.queryByRole("heading")).toBeNull();
  });

  it("el nivel pone su clase: la del espacio y la del conmutador de subvistas", () => {
    const { container, unmount } = pintar({ nivel: "espacio" });
    expect(container.querySelector("nav")).toHaveClass("silice-barra-espacio");
    expect(container.querySelector("nav")).not.toHaveClass("silice-barra-espacio--subvista");
    unmount();
    const subvista = pintar({ nivel: "subvista", etiqueta: "Vistas de Presupuesto" });
    const nav = subvista.container.querySelector("nav");
    expect(nav).toHaveClass("silice-barra-espacio", "silice-barra-espacio--subvista");
    expect(within(nav as HTMLElement).getAllByRole("link")[0]).toHaveClass("silice-barra-espacio__pestana");
  });

  it("Tab recorre los enlaces en orden", async () => {
    const usuario = userEvent.setup();
    pintar();
    await usuario.tab();
    expect(screen.getByRole("link", { name: "Resumen" })).toHaveFocus();
    await usuario.tab();
    expect(screen.getByRole("link", { name: "Presupuesto" })).toHaveFocus();
    await usuario.tab();
    expect(screen.getByRole("link", { name: "Tramos" })).toHaveFocus();
  });
});

describe("BarraDeEspacio: regla de omisión del nivel subvista (adenda A.1)", () => {
  it("con una sola pestaña no pinta nada", () => {
    const { container } = pintar({ nivel: "subvista", etiqueta: "Vistas de Presupuesto", pestanas: [PESTANAS[1]!] });
    expect(container).toBeEmptyDOMElement();
  });

  it("sin pestañas no pinta nada", () => {
    const { container } = pintar({ nivel: "subvista", etiqueta: "Vistas de Presupuesto", pestanas: [] });
    expect(container).toBeEmptyDOMElement();
  });

  it("con dos pestañas sí pinta el conmutador", () => {
    pintar({ nivel: "subvista", etiqueta: "Vistas de Presupuesto", pestanas: PESTANAS.slice(0, 2), activa: "resumen" });
    expect(screen.getByRole("navigation", { name: "Vistas de Presupuesto" })).toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(2);
  });

  it("el nivel espacio con una sola pestaña sí la pinta (la omisión es solo de las subvistas)", () => {
    pintar({ pestanas: [PESTANAS[0]!], activa: "resumen" });
    expect(screen.getByRole("link", { name: "Resumen" })).toBeInTheDocument();
  });
});

// Oráculos escritos a mano: qué pantalla exige qué permiso está en shell/rutas.ts; aquí solo se prueba que la barra no
// ofrece lo que la cuenta no puede usar.
describe("pestanasUsables", () => {
  const producir = ESPACIOS.produccion.herramientas;

  it("sin acciones no incluye «Costos del período» (pide registrar_costos_produccion)", () => {
    expect(ids(pestanasUsables(producir, rutaDe, [], false, []))).not.toContain("costos");
  });

  it("con la acción de costos incluye costos y costo por tonelada, y nada que pida otra acción", () => {
    expect(ids(pestanasUsables(producir, rutaDe, ["registrar_costos_produccion"], false, []))).toEqual(["costos", "costo-tonelada"]);
  });

  it("con operar_arenera ofrece el resto de Producción en el orden de la tabla", () => {
    expect(ids(pestanasUsables(producir, rutaDe, ["operar_arenera"], false, []))).toEqual(["resumen", "existencias", "receta", "mezcla"]);
  });

  it("con el módulo de producción apagado no queda ninguna pestaña de Producción", () => {
    const todas = ["operar_arenera", "registrar_costos_produccion"];
    expect(pestanasUsables(producir, rutaDe, todas, false, [])).toHaveLength(6);
    expect(pestanasUsables(producir, rutaDe, todas, false, ["produccion"])).toEqual([]);
  });

  it("con modo entrega no aparece el Simulador de listas", () => {
    const precios = ESPACIOS.precios.herramientas;
    const acciones = ["editar_hoja", "leer_proyecto", "administrar_precios"];
    expect(ids(pestanasUsables(precios, rutaDe, acciones, false, []))).toEqual(["listas", "catalogo", "indices", "simulador"]);
    expect(ids(pestanasUsables(precios, rutaDe, acciones, true, []))).toEqual(["listas", "catalogo", "indices"]);
  });

  it("devuelve id, título y la ruta que da rutaDe, en el orden de la tabla", () => {
    expect(pestanasUsables(ESPACIOS.precios.herramientas, rutaDe, ["leer_proyecto"], false, [])).toEqual([
      { id: "catalogo", titulo: "Catálogo de partidas e insumos", ruta: "/empresa/precios" },
    ]);
  });

  it("también filtra las subvistas: sin editar_hoja, Presupuesto queda con una sola (y la barra de subvistas no se pinta)", () => {
    const subvistas = SUBVISTAS.presupuesto ?? [];
    const solasPartidas = pestanasUsables(subvistas, (h) => `/p/${h.id}`, ["leer_proyecto"], false, []);
    expect(ids(solasPartidas)).toEqual([""]);
    const { container } = render(
      <MemoryRouter>
        <BarraDeEspacio etiqueta="Vistas de Presupuesto" pestanas={solasPartidas} activa="" nivel="subvista" />
      </MemoryRouter>,
    );
    expect(container).toBeEmptyDOMElement();
    expect(ids(pestanasUsables(subvistas, (h) => `/p/${h.id}`, ["leer_proyecto", "editar_hoja"], false, []))).toEqual(["", "componer"]);
  });

  it("una herramienta cuya pantalla no existe no se ofrece", () => {
    const rara = [{ id: "x", titulo: "X", pagina: "no_existe" }];
    expect(pestanasUsables(rara, rutaDe, ["operar_arenera"], false, [])).toEqual([]);
  });
});

// jsdom no calcula CSS: las reglas se leen del fuente. Medidas y estados exactos: diseño visual §1.2 y adenda A.3.
describe("BarraDeEspacio: estilos", () => {
  const hoja = () => leer("marco/BarraDeEspacio.scss");
  // Bloque `{ … }` que sigue a `apertura`, con sus llaves anidadas.
  const bloque = (apertura: string) => {
    const fuente = hoja();
    const i = fuente.indexOf(apertura);
    if (i < 0) return "(no hay regla " + apertura + ")";
    let nivel = 0;
    for (let j = fuente.indexOf("{", i); j < fuente.length; j++) {
      if (fuente[j] === "{") nivel++;
      if (fuente[j] === "}" && --nivel === 0) return fuente.slice(i, j + 1);
    }
    return "";
  };

  it("el componente importa su hoja de estilos", () => {
    expect(leer("marco/BarraDeEspacio.tsx")).toMatch(/import\s+"\.\/BarraDeEspacio\.scss"/);
  });

  it("no declara anchos fijos (px ni rem) en width, inline-size ni sus mínimos y máximos", () => {
    const fijos = hoja().match(/(?:^|[\s;{])(?:min-|max-)?(?:width|inline-size)\s*:\s*[\d.]+(?:px|rem|em)\b/g);
    expect(fijos).toBeNull();
  });

  it("parte en renglones y no desborda ni oculta pestañas", () => {
    const nav = bloque(".silice-barra-espacio {");
    expect(nav).toMatch(/display:\s*flex/);
    expect(nav).toMatch(/flex-wrap:\s*wrap/);
    expect(nav).toMatch(/align-items:\s*stretch/);
    expect(nav).toMatch(/gap:\s*0/);
    expect(nav).toMatch(/padding-inline:\s*1rem/);
    expect(nav).toMatch(/background-color:\s*var\(--cds-layer-01\)/);
    expect(nav).toMatch(/border-block-end:\s*1px solid var\(--cds-border-subtle\)/);
    expect(hoja()).not.toMatch(/overflow(-x)?:\s*(auto|scroll|hidden)/);
  });

  it("la pestaña del espacio: 2,5 rem, body-compact-01, raya reservada y sin subrayado", () => {
    const pestana = bloque(".silice-barra-espacio__pestana {");
    expect(pestana).toMatch(/min-block-size:\s*2\.5rem/);
    expect(pestana).toMatch(/padding-block:\s*0\.5rem/);
    expect(pestana).toMatch(/padding-inline:\s*0\.75rem/);
    expect(pestana).toMatch(/type-style\("body-compact-01"\)/);
    expect(pestana).toMatch(/white-space:\s*nowrap/);
    expect(pestana).toMatch(/text-decoration:\s*none/);
    expect(pestana).toMatch(/color:\s*var\(--cds-text-secondary\)/);
    expect(pestana).toMatch(/font-weight:\s*400/);
    expect(pestana).toMatch(/border-block-end:\s*3px solid transparent/);
  });

  it("hover, activa y foco del espacio usan tokens, la raya del complementario y el foco hacia adentro", () => {
    const hover = bloque("&:hover {");
    expect(hover).toMatch(/background-color:\s*var\(--cds-layer-hover-01\)/);
    expect(hover).toMatch(/color:\s*var\(--cds-text-primary\)/);
    const activa = bloque('&[aria-current="page"] {');
    expect(activa).toMatch(/color:\s*var\(--cds-text-primary\)/);
    expect(activa).toMatch(/font-weight:\s*600/);
    expect(activa).toMatch(/background-color:\s*var\(--cds-background\)/);
    expect(activa).toMatch(/border-block-end:\s*3px solid var\(--silice-complementario\)/);
    const foco = bloque("&:focus-visible {");
    expect(foco).toMatch(/outline:\s*2px solid var\(--cds-focus\)/);
    expect(foco).toMatch(/outline-offset:\s*-2px/);
  });

  it("con letra grande compacta la pestaña (2 rem, 0,375 rem y 0,625 rem) con el mixin de _umbrales", () => {
    expect(hoja()).toMatch(/@use "umbrales" as u;/);
    const compacta = bloque("@include u.con-letra-grande {");
    expect(compacta).toMatch(/min-block-size:\s*2rem/);
    expect(compacta).toMatch(/padding-block:\s*0\.375rem/);
    expect(compacta).toMatch(/padding-inline:\s*0\.625rem/);
  });

  it("el conmutador de subvistas: compacto, enmarcado, label-01, divisores y raya de 2 px arriba", () => {
    const conmutador = bloque(".silice-barra-espacio--subvista {");
    expect(conmutador).toMatch(/display:\s*inline-flex/);
    expect(conmutador).toMatch(/flex-wrap:\s*wrap/);
    expect(conmutador).toMatch(/align-self:\s*flex-start/);
    expect(conmutador).toMatch(/margin:\s*0\.75rem 1rem 0/);
    expect(conmutador).toMatch(/inline-size:\s*fit-content/);
    expect(conmutador).toMatch(/max-inline-size:\s*calc\(100% - 2rem\)/);
    expect(conmutador).toMatch(/border:\s*1px solid var\(--cds-border-subtle\)/);
    expect(conmutador).toMatch(/padding-inline:\s*0/);
    const pestana = bloque(".silice-barra-espacio--subvista .silice-barra-espacio__pestana {");
    expect(pestana).toMatch(/min-block-size:\s*1\.75rem/);
    expect(pestana).toMatch(/padding-block:\s*0\.25rem/);
    expect(pestana).toMatch(/padding-inline:\s*0\.625rem/);
    expect(pestana).toMatch(/type-style\("label-01"\)/);
    expect(pestana).toMatch(/background-color:\s*var\(--cds-layer-01\)/);
    expect(pestana).toMatch(/border-block-start:\s*2px solid transparent/);
    expect(pestana).toMatch(/border-block-end:\s*0/);
    expect(pestana).toMatch(/border-inline-end:\s*1px solid var\(--cds-border-subtle\)/);
    expect(pestana).toMatch(/&:last-child\s*\{[^}]*border-inline-end:\s*0/);
    const activa = pestana.slice(pestana.indexOf('&[aria-current="page"]'));
    expect(activa).toMatch(/background-color:\s*var\(--cds-layer-selected-01\)/);
    expect(activa).toMatch(/border-block-start:\s*2px solid var\(--silice-complementario\)/);
    expect(activa).toMatch(/font-weight:\s*600/);
  });

  it("el conmutador compacta con letra grande a 1,625 rem", () => {
    const compacta = bloque("@include u.con-letra-grande {");
    expect(compacta).toMatch(/min-block-size:\s*1\.625rem/);
  });

  it("sin colores nuevos: solo tokens, sin sombras ni animaciones, y sin esquinas redondeadas", () => {
    expect(hoja()).not.toMatch(/#[0-9a-fA-F]{3,8}\b|rgba?\(/);
    expect(hoja()).not.toMatch(/box-shadow|transition|animation|border-radius:\s*[1-9]/);
  });
});
