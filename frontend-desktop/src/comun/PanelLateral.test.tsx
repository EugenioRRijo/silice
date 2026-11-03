import { fileURLToPath } from "node:url";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import * as sass from "sass";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { PanelLateral } from "./PanelLateral";

// F4, Tareas 6 y 7: el panel acoplado a la derecha del contenido (el APU de una partida, el registro de cambios de una
// versión). No es modal: no atrapa el foco ni tapa la pantalla, salvo por debajo del umbral de la letra. Los textos
// esperados están escritos a mano a partir del plan; datos ficticios.

// Dos disparadores, como dos filas de una tabla: cada uno abre el panel con su título.
function Banco({ ancho }: { ancho?: "normal" | "ancho" }) {
  const [abierto, setAbierto] = useState<string | null>(null);
  return (
    <div>
      <button type="button" onClick={() => setAbierto("E-01")}>
        Abrir E-01
      </button>
      <button type="button" onClick={() => setAbierto("E-02")}>
        Abrir E-02
      </button>
      <PanelLateral titulo={`APU de ${abierto ?? ""}`} abierto={abierto !== null} alCerrar={() => setAbierto(null)} ancho={ancho}>
        <p>Contenido del panel</p>
        {/* Un campo que usa Esc para lo suyo (como CampoDeCelda, que restaura el valor) y lo marca con preventDefault. */}
        <input
          aria-label="Cantidad"
          onKeyDown={(e) => {
            if (e.key === "Escape") e.preventDefault();
          }}
        />
      </PanelLateral>
    </div>
  );
}

describe("PanelLateral", () => {
  test("cerrado no pinta nada", () => {
    render(<Banco />);
    expect(screen.queryByRole("complementary")).toBeNull();
    expect(screen.queryByText("Contenido del panel")).toBeNull();
  });

  test("abierto es una región complementaria con el nombre de su h2, y el foco va al h2", async () => {
    const u = userEvent.setup();
    render(<Banco />);
    await u.click(screen.getByRole("button", { name: "Abrir E-01" }));
    const panel = screen.queryByRole("complementary", { name: "APU de E-01" });
    expect(panel, "el panel «APU de E-01»").not.toBeNull();
    const titulo = screen.getByRole("heading", { level: 2, name: "APU de E-01" });
    expect(titulo).toHaveFocus();
    expect(panel).toHaveTextContent("Contenido del panel");
    expect(panel).toHaveClass("silice-panel-lateral");
    expect(panel).not.toHaveClass("silice-panel-lateral--ancho");
  });

  test("Esc lo cierra y el foco vuelve al disparador", async () => {
    const u = userEvent.setup();
    render(<Banco />);
    await u.click(screen.getByRole("button", { name: "Abrir E-01" }));
    expect(screen.queryByRole("complementary"), "el panel abierto").not.toBeNull();
    await u.keyboard("{Escape}");
    expect(screen.queryByRole("complementary")).toBeNull();
    expect(screen.getByRole("button", { name: "Abrir E-01" })).toHaveFocus();
  });

  test("«Cerrar» lo cierra y el foco vuelve al disparador", async () => {
    const u = userEvent.setup();
    render(<Banco />);
    await u.click(screen.getByRole("button", { name: "Abrir E-02" }));
    const cerrar = screen.queryByRole("button", { name: "Cerrar" });
    expect(cerrar, "el botón «Cerrar»").not.toBeNull();
    await u.click(cerrar!);
    expect(screen.queryByRole("complementary")).toBeNull();
    expect(screen.getByRole("button", { name: "Abrir E-02" })).toHaveFocus();
  });

  test("abierto desde otra fila, el foco vuelve a la última que lo abrió", async () => {
    const u = userEvent.setup();
    render(<Banco />);
    await u.click(screen.getByRole("button", { name: "Abrir E-01" }));
    await u.click(screen.getByRole("button", { name: "Abrir E-02" }));
    const titulo = screen.queryByRole("heading", { level: 2, name: "APU de E-02" });
    expect(titulo, "el título «APU de E-02»").not.toBeNull();
    expect(titulo).toHaveFocus();
    await u.keyboard("{Escape}");
    expect(screen.getByRole("button", { name: "Abrir E-02" })).toHaveFocus();
  });

  test("el Esc que un campo de dentro ya usó (preventDefault) no cierra el panel", async () => {
    const u = userEvent.setup();
    render(<Banco />);
    await u.click(screen.getByRole("button", { name: "Abrir E-01" }));
    const campo = screen.queryByRole("textbox", { name: "Cantidad" });
    expect(campo, "el campo de dentro").not.toBeNull();
    await u.click(campo!);
    await u.keyboard("{Escape}");
    expect(screen.queryByRole("complementary", { name: "APU de E-01" })).not.toBeNull();
  });

  test("«ancho» le da su clase", async () => {
    const u = userEvent.setup();
    render(<Banco ancho="ancho" />);
    await u.click(screen.getByRole("button", { name: "Abrir E-01" }));
    expect(screen.queryByRole("complementary")?.className ?? "").toMatch(/\bsilice-panel-lateral--ancho\b/);
  });
});

// Pasada de navegador del cierre de F4 (H2 y H3). Si en `silice-con-panel` no caben el panel, el espacio entre los dos y
// 32 rem de contenido, el panel pasa por encima (clase `--superpuesto`) y lo que tapa queda `inert`: el foco no llega a lo
// que no se ve. Junto al contenido no cambia nada. jsdom no maqueta: se fijan el rem, el ancho del contenedor y las cajas.
// Con 16 px de rem el ancho necesita (40 + 1 + 32) × 16 = 1168 px y el normal (24 + 1 + 32) × 16 = 912 px.
interface Caja {
  left: number;
  right: number;
  top: number;
  bottom: number;
}

function Pagina({ ancho, modo }: { ancho?: "normal" | "ancho"; modo?: "acoplado" | "en-capa" }) {
  const [abierto, setAbierto] = useState(false);
  return (
    <div>
      <nav data-zona="lateral">
        <a href="#obra">Obra ficticia 02</a>
      </nav>
      <div className="silice-con-panel" data-zona="contenedor">
        <div data-zona="contenido">
          <button type="button" onClick={() => setAbierto(true)}>
            Abrir el APU de E-01
          </button>
          <div data-zona="ya-inerte" inert>
            <button type="button">Detrás de un diálogo</button>
          </div>
        </div>
        <PanelLateral titulo="APU de E-01" abierto={abierto} alCerrar={() => setAbierto(false)} ancho={ancho} modo={modo}>
          <p>Contenido del panel</p>
        </PanelLateral>
      </div>
    </div>
  );
}

describe("PanelLateral: por encima cuando no cabe junto al contenido", () => {
  let anchoDelContenedor = 0;
  const cajas: Record<string, Caja> = {
    // El panel por encima a la derecha, bajo la barra superior; el contenido se cruza con él y la barra lateral no.
    panel: { left: 600, right: 1000, top: 48, bottom: 768 },
    contenido: { left: 320, right: 1000, top: 120, bottom: 2400 },
    "ya-inerte": { left: 320, right: 1000, top: 200, bottom: 260 },
    lateral: { left: 0, right: 300, top: 48, bottom: 768 },
  };
  const original = {
    rect: Element.prototype.getBoundingClientRect,
    ancho: Object.getOwnPropertyDescriptor(Element.prototype, "clientWidth"),
  };

  beforeEach(() => {
    document.documentElement.style.fontSize = "16px";
    vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function (this: Element) {
      const zona = this.classList.contains("silice-panel-lateral") ? "panel" : (this.getAttribute("data-zona") ?? "");
      const c = cajas[zona] ?? { left: 0, right: 0, top: 0, bottom: 0 };
      return { ...c, x: c.left, y: c.top, width: c.right - c.left, height: c.bottom - c.top, toJSON: () => c } as DOMRect;
    });
    Object.defineProperty(Element.prototype, "clientWidth", {
      configurable: true,
      get(this: Element) {
        return this.classList.contains("silice-con-panel") ? anchoDelContenedor : 0;
      },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    Element.prototype.getBoundingClientRect = original.rect;
    if (original.ancho) Object.defineProperty(Element.prototype, "clientWidth", original.ancho);
    document.documentElement.style.fontSize = "";
  });

  const zona = (nombre: string) => document.querySelector(`[data-zona="${nombre}"]`)!;

  test("ancho, en 1100 px (le faltan 68): por encima, lo tapado queda inerte y lo que no tapa no", async () => {
    anchoDelContenedor = 1100;
    const u = userEvent.setup();
    render(<Pagina ancho="ancho" />);
    await u.click(screen.getByRole("button", { name: "Abrir el APU de E-01" }));
    const panel = screen.getByRole("complementary", { name: "APU de E-01" });
    expect(panel).toHaveClass("silice-panel-lateral--superpuesto");
    expect(zona("contenido")).toHaveAttribute("inert");
    expect(zona("lateral")).not.toHaveAttribute("inert");
    expect(screen.getByRole("heading", { level: 2, name: "APU de E-01" })).toHaveFocus();
  });

  test("al cerrar se quita el inerte que puso (no el de otro) y el foco vuelve al disparador", async () => {
    anchoDelContenedor = 1100;
    const u = userEvent.setup();
    render(<Pagina ancho="ancho" />);
    await u.click(screen.getByRole("button", { name: "Abrir el APU de E-01" }));
    expect(zona("contenido")).toHaveAttribute("inert");
    await u.keyboard("{Escape}");
    expect(screen.queryByRole("complementary")).toBeNull();
    expect(zona("contenido")).not.toHaveAttribute("inert");
    expect(zona("ya-inerte")).toHaveAttribute("inert");
    expect(screen.getByRole("button", { name: "Abrir el APU de E-01" })).toHaveFocus();
  });

  test("ancho, en 1168 px (justo cabe): junto al contenido, sin inerte", async () => {
    anchoDelContenedor = 1168;
    const u = userEvent.setup();
    render(<Pagina ancho="ancho" />);
    await u.click(screen.getByRole("button", { name: "Abrir el APU de E-01" }));
    expect(screen.getByRole("complementary", { name: "APU de E-01" })).not.toHaveClass("silice-panel-lateral--superpuesto");
    expect(zona("contenido")).not.toHaveAttribute("inert");
  });

  test("normal, en 1000 px: cabe (necesita 912) y va junto al contenido", async () => {
    anchoDelContenedor = 1000;
    const u = userEvent.setup();
    render(<Pagina />);
    await u.click(screen.getByRole("button", { name: "Abrir el APU de E-01" }));
    expect(screen.getByRole("complementary", { name: "APU de E-01" })).not.toHaveClass("silice-panel-lateral--superpuesto");
  });

  test("al agrandarse la ventana vuelve junto al contenido y suelta lo tapado", async () => {
    anchoDelContenedor = 1100;
    const u = userEvent.setup();
    render(<Pagina ancho="ancho" />);
    await u.click(screen.getByRole("button", { name: "Abrir el APU de E-01" }));
    expect(zona("contenido")).toHaveAttribute("inert");
    anchoDelContenedor = 1600;
    await act(async () => {
      window.dispatchEvent(new Event("resize"));
    });
    expect(screen.getByRole("complementary", { name: "APU de E-01" })).not.toHaveClass("silice-panel-lateral--superpuesto");
    expect(zona("contenido")).not.toHaveAttribute("inert");
  });

  test("en la capa de un diálogo («en-capa»): siempre por encima y sin tocar lo de detrás (la capa ya lo deja inerte)", async () => {
    anchoDelContenedor = 4000;
    const u = userEvent.setup();
    render(<Pagina ancho="ancho" modo="en-capa" />);
    await u.click(screen.getByRole("button", { name: "Abrir el APU de E-01" }));
    expect(screen.getByRole("complementary", { name: "APU de E-01" })).toHaveClass("silice-panel-lateral--superpuesto");
    expect(zona("contenido")).not.toHaveAttribute("inert");
  });
});

// jsdom no dibuja: se compila el SCSS real y se leen las reglas (como en `componer/estilosComponer.test.ts`).
const compilar = (ruta: string) => sass.compile(fileURLToPath(new URL(ruta, import.meta.url))).css;

describe("PanelLateral: estilos", () => {
  const css = compilar("./PanelLateral.scss");

  test("acoplado: 24 rem, o 40 rem el ancho, y el contenido que lo acompaña se encoge sin desbordar", () => {
    expect(css).toMatch(/\.silice-panel-lateral\s*\{[^}]*inline-size:\s*24rem/);
    expect(css).toMatch(/\.silice-panel-lateral--ancho\s*\{[^}]*inline-size:\s*40rem/);
    expect(css).toMatch(/\.silice-con-panel\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\) auto/);
  });

  // Pasada de navegador del cierre de F4 (H1 y H2): ya no lo decide el umbral de la letra sino el ancho real (la prueba de
  // comportamiento está arriba); la regla del panel por encima es una clase y vale igual dentro de la capa de un diálogo.
  test("por encima: fijo bajo la barra superior, por encima de las columnas fijas, con fondo y su propio desplazamiento", () => {
    const regla = /\.silice-panel-lateral--superpuesto\s*\{([^}]*)\}/.exec(css)?.[1] ?? "";
    expect(regla).toMatch(/position:\s*fixed/);
    expect(regla).toMatch(/inset-block:\s*3rem 0/);
    expect(regla).toMatch(/inline-size:\s*min\(24rem, 100%\)/);
    expect(regla).toMatch(/max-inline-size:\s*100%/);
    expect(regla).toMatch(/overflow-y:\s*auto/);
    expect(regla).toMatch(/background:\s*var\(--cds-layer-01\)/);
    // Por encima de la columna fija de las tablas (z-index 1 en `paginas/hoja/hoja.scss`) y bajo la barra superior (8000).
    const capa = Number(/z-index:\s*(\d+)/.exec(regla)?.[1] ?? "NaN");
    expect(capa).toBeGreaterThan(1);
    expect(capa).toBeLessThan(8000);
    expect(css).toMatch(/\.silice-panel-lateral--ancho\.silice-panel-lateral--superpuesto\s*\{[^}]*inline-size:\s*min\(40rem, 100%\)/);
    // El contenido que lo acompaña recupera todo el ancho.
    expect(css).toMatch(/\.silice-con-panel:has\(> \.silice-panel-lateral--superpuesto\)\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\)\s*;/);
  });

  test("ya no depende del umbral de la letra: ninguna regla de medios lo vuelve fijo", () => {
    expect(css).not.toMatch(/@media[^{]*\{[^@]*\.silice-panel-lateral\s*\{[^}]*position:\s*fixed/);
  });
});
