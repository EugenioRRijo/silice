import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router";
import { describe, expect, it } from "vitest";
import { BarraDeObra } from "./BarraDeObra";
import type { SeccionId } from "./secciones";

// Con `css: false` el `?raw` de un .scss llega vacío: el fuente se lee con el módulo de Node (como BarraDeEspacio.test.tsx).
interface Fs {
  readFileSync(ruta: string, codificacion: string): string;
}
const nodo = (
  globalThis as unknown as { process: { cwd(): string; getBuiltinModule(nombre: "node:fs"): Fs } }
).process;
const leerCss = (ruta: string): string => nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/${ruta}`, "utf-8");

function Ruta() {
  return <p data-testid="ruta">{useLocation().pathname}</p>;
}

function pintar(propiedades: Partial<Parameters<typeof BarraDeObra>[0]> = {}) {
  const seccion: SeccionId = propiedades.seccion ?? "presupuesto";
  return render(
    <MemoryRouter initialEntries={["/obra/a.db/3/presupuesto"]}>
      <BarraDeObra carpeta="a.db" obraId={3} nombre="Galpón Norte" seccion={seccion} {...propiedades} />
      <Ruta />
    </MemoryRouter>,
  );
}

describe("BarraDeObra: el nombre y la Portada", () => {
  it("el nombre de la obra es un enlace a su Portada, con la línea «Portada de la obra»", () => {
    pintar();
    const enlace = screen.getByRole("link", { name: /Galpón Norte/ });
    expect(enlace).toHaveAttribute("href", "/obra/a.db/3/resumen");
    expect(enlace).toHaveTextContent("Portada de la obra");
  });

  it("en la Portada (y su Tablero) el enlace es la página actual y ninguna herramienta lo es", () => {
    pintar({ seccion: "resumen", subvista: "tablero" });
    expect(screen.getByRole("link", { name: /Galpón Norte/ })).toHaveAttribute("aria-current", "page");
    const herramientas = screen.getByRole("navigation", { name: "Herramientas de la obra" });
    expect(within(herramientas).queryAllByRole("link").filter((l) => l.getAttribute("aria-current") === "page")).toHaveLength(0);
  });
});

describe("BarraDeObra: las herramientas", () => {
  it("Presupuestar, Auditar y Anticipar son enlaces a la primera sección de cada una", () => {
    pintar();
    const nav = screen.getByRole("navigation", { name: "Herramientas de la obra" });
    expect(within(nav).getAllByRole("link").map((l) => l.textContent)).toEqual(["Presupuestar", "Auditar", "Anticipar"]);
    expect(within(nav).getByRole("link", { name: "Presupuestar" })).toHaveAttribute("href", "/obra/a.db/3/presupuesto");
    expect(within(nav).getByRole("link", { name: "Auditar" })).toHaveAttribute("href", "/obra/a.db/3/aprobaciones");
    expect(within(nav).getByRole("link", { name: "Anticipar" })).toHaveAttribute("href", "/obra/a.db/3/control");
  });

  it("estando en Presupuesto, solo Presupuestar lleva aria-current", () => {
    pintar();
    expect(screen.getByRole("link", { name: "Presupuestar" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: "Auditar" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("link", { name: "Anticipar" })).not.toHaveAttribute("aria-current");
  });

  it.each([
    ["presupuesto", "componer", "Presupuestar"],
    ["mercado", "actualizar", "Presupuestar"],
    ["aprobaciones", "entregar", "Auditar"],
    ["control", "escenarios", "Anticipar"],
    ["riesgo", undefined, "Anticipar"],
  ] as const)("en %s/%s la herramienta actual es %s", (seccion, subvista, actual) => {
    pintar({ seccion, subvista });
    expect(screen.getByRole("link", { name: actual })).toHaveAttribute("aria-current", "page");
  });

  it("en Versiones ninguna herramienta es la actual", () => {
    pintar({ seccion: "versiones" });
    expect(screen.queryAllByRole("link").filter((l) => l.getAttribute("aria-current") === "page")).toHaveLength(0);
  });

  it("un clic en Auditar navega a su ruta", async () => {
    pintar();
    await userEvent.click(screen.getByRole("link", { name: "Auditar" }));
    expect(screen.getByTestId("ruta")).toHaveTextContent("/obra/a.db/3/aprobaciones");
  });

  it("con las secciones usables, no ofrece la herramienta sin ninguna y salta la sección que no puede", () => {
    pintar({ usables: ["tramos", "control"] });
    expect(screen.queryByRole("link", { name: "Auditar" })).toBeNull();
    expect(screen.getByRole("link", { name: "Presupuestar" })).toHaveAttribute("href", "/obra/a.db/3/tramos");
    expect(screen.getByRole("link", { name: "Anticipar" })).toHaveAttribute("href", "/obra/a.db/3/control");
  });

  it("la carpeta de la empresa va como «empresa» en las rutas", () => {
    pintar({ carpeta: null });
    expect(screen.getByRole("link", { name: "Presupuestar" })).toHaveAttribute("href", "/obra/empresa/3/presupuesto");
  });
});

describe("BarraDeObra: la segunda fila (opciones de la herramienta activa)", () => {
  const opciones = (nombre: string) => within(screen.getByRole("navigation", { name: nombre }));

  it("en Presupuestar ofrece sus seis opciones, con la actual marcada", () => {
    pintar({ seccion: "presupuesto" });
    const nav = opciones("Opciones de Presupuestar");
    expect(nav.getAllByRole("link").map((l) => l.textContent)).toEqual([
      "Partidas",
      "Componer un APU",
      "Espacio, plan y ajustes",
      "Tramos de la vía",
      "Plano o cómputo",
      "Precios de mercado",
    ]);
    expect(nav.getByRole("link", { name: "Espacio, plan y ajustes" })).toHaveAttribute("href", "/obra/a.db/3/presupuesto/pestanas");
    expect(nav.getByRole("link", { name: "Componer un APU" })).toHaveAttribute("href", "/obra/a.db/3/presupuesto/componer");
    expect(nav.getByRole("link", { name: "Partidas" })).toHaveAttribute("aria-current", "page");
    expect(nav.getAllByRole("link").filter((l) => l.getAttribute("aria-current") === "page")).toHaveLength(1);
  });

  it("marca la opción de la subvista abierta", () => {
    pintar({ seccion: "control", subvista: "reajuste" });
    const nav = opciones("Opciones de Anticipar");
    expect(nav.getByRole("link", { name: "Reajuste de precios" })).toHaveAttribute("aria-current", "page");
    expect(nav.getByRole("link", { name: "Control de obra" })).not.toHaveAttribute("aria-current");
  });

  it("en Auditar ofrece Aprobar, Revisar un paquete y Entregar", () => {
    pintar({ seccion: "aprobaciones", subvista: "entregar" });
    const nav = opciones("Opciones de Auditar");
    expect(nav.getAllByRole("link").map((l) => l.textContent)).toEqual(["Aprobar", "Revisar un paquete", "Entregar"]);
    expect(nav.getByRole("link", { name: "Entregar" })).toHaveAttribute("aria-current", "page");
  });

  it("en la Portada ofrece Resumen y Tablero", () => {
    pintar({ seccion: "resumen", subvista: "tablero" });
    const nav = opciones("Opciones de la portada");
    expect(nav.getAllByRole("link").map((l) => l.textContent)).toEqual(["Resumen", "Tablero"]);
    expect(nav.getByRole("link", { name: "Tablero" })).toHaveAttribute("aria-current", "page");
  });

  it("en Versiones no hay segunda fila", () => {
    pintar({ seccion: "versiones" });
    expect(screen.getAllByRole("navigation")).toHaveLength(1);
  });

  it("solo ofrece las opciones de secciones que la cuenta puede usar", () => {
    pintar({ seccion: "presupuesto", usables: ["presupuesto", "mercado", "control"] });
    expect(opciones("Opciones de Presupuestar").getAllByRole("link").map((l) => l.textContent)).toEqual([
      "Partidas",
      "Componer un APU",
      "Espacio, plan y ajustes",
      "Precios de mercado",
    ]);
  });

  it("un clic en una opción navega a su ruta", async () => {
    pintar({ seccion: "presupuesto" });
    await userEvent.click(opciones("Opciones de Presupuestar").getByRole("link", { name: "Tramos de la vía" }));
    expect(screen.getByTestId("ruta")).toHaveTextContent("/obra/a.db/3/tramos");
  });
});

describe("BarraDeObra: el menú de versión", () => {
  it("es un botón con la etiqueta visible «Versión» y trae sus tres opciones", async () => {
    pintar();
    const boton = screen.getByRole("button", { name: /Versión/ });
    expect(boton).toHaveTextContent("Versión");
    await userEvent.click(boton);
    const menu = await screen.findByRole("menu");
    expect(within(menu).getAllByRole("menuitem").map((i) => i.textContent)).toEqual(["Versiones", "Pedir aprobación", "Entregar al cliente"]);
  });

  it.each([
    ["Versiones", "/obra/a.db/3/versiones"],
    ["Pedir aprobación", "/obra/a.db/3/aprobaciones"],
    ["Entregar al cliente", "/obra/a.db/3/aprobaciones/entregar"],
  ])("«%s» lleva a %s", async (opcion, ruta) => {
    pintar();
    await userEvent.click(screen.getByRole("button", { name: /Versión/ }));
    await userEvent.click(await screen.findByRole("menuitem", { name: opcion }));
    expect(screen.getByTestId("ruta")).toHaveTextContent(ruta);
  });

  it("sin permiso para Versiones ni Aprobaciones no se ofrece el menú", () => {
    pintar({ usables: ["presupuesto"] });
    expect(screen.queryByRole("button", { name: /Versión/ })).toBeNull();
  });
});

describe("BarraDeObra: la acción principal", () => {
  it("pinta lo que se le pasa en la ranura, y nada si no se le pasa", () => {
    const { unmount } = pintar({ accion: <button type="button">Guardar versión</button> });
    expect(screen.getByRole("button", { name: "Guardar versión" })).toBeInTheDocument();
    unmount();
    pintar();
    expect(screen.queryByRole("button", { name: "Guardar versión" })).toBeNull();
  });
});

describe("BarraDeObra: estilos", () => {
  const css = leerCss("marco/BarraDeObra.scss");
  it("fondo de la hoja, filete de la línea y alto de 3,25 rem", () => {
    expect(css).toMatch(/background-color:\s*var\(--silice-hoja\)/);
    expect(css).toMatch(/border-block-end:\s*1px solid var\(--silice-linea\)/);
    expect(css).toMatch(/block-size:\s*3\.25rem/);
  });
  it("la herramienta actual lleva una raya de 2 px en el complementario", () => {
    expect(css).toMatch(/aria-current="page"[^}]*border-block-end:\s*2px solid var\(--silice-complementario\)/s);
  });
  it("sin tamaños de letra en px ni colores fijos", () => {
    expect(css).not.toMatch(/font-size:\s*[\d.]+px/);
    expect(css).not.toMatch(/#[0-9a-fA-F]{3,8}\b|rgba?\(/);
  });
});
