import { fileURLToPath } from "node:url";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import * as sass from "sass";
import { describe, expect, test } from "vitest";
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

// jsdom no dibuja: se compila el SCSS real y se leen las reglas (como en `componer/estilosComponer.test.ts`).
const compilar = (ruta: string) => sass.compile(fileURLToPath(new URL(ruta, import.meta.url))).css;

describe("PanelLateral: estilos", () => {
  const css = compilar("./PanelLateral.scss");

  test("acoplado: 24 rem, o 40 rem el ancho, y el contenido que lo acompaña se encoge sin desbordar", () => {
    expect(css).toMatch(/\.silice-panel-lateral\s*\{[^}]*inline-size:\s*24rem/);
    expect(css).toMatch(/\.silice-panel-lateral--ancho\s*\{[^}]*inline-size:\s*40rem/);
    expect(css).toMatch(/\.silice-con-panel\s*\{[^}]*grid-template-columns:\s*minmax\(0, 1fr\) auto/);
  });

  test.each([
    ["normal", "1055.98px"],
    ["grande", "1535.98px"],
    ["muy-grande", "1919.98px"],
  ])("por debajo del umbral de la letra %s pasa por encima, sin ancho fijo y a lo más el 100 %%", (escala, umbral) => {
    const medio = new RegExp(
      `@media \\(max-width: ${umbral.replace(".", "\\.")}\\)\\s*\\{[\\s\\S]*?html\\[data-silice-letra=["']?${escala}["']?\\] \\.silice-panel-lateral\\s*\\{([^}]*)\\}`,
    ).exec(css);
    expect(medio?.[1] ?? "", `la regla de ${escala} por debajo de ${umbral}`).toMatch(/position:\s*fixed/);
    expect(medio?.[1] ?? "").toMatch(/max-inline-size:\s*100%/);
    expect(medio?.[1] ?? "").not.toMatch(/(?:^|[;\s])inline-size:\s*\d/);
  });
});
