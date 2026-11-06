// D10 de la tanda de detalles (hallazgo 19 del recorrido del 01-11-2026): botones sin nombre accesible. Carbon pone en
// cada pestaña un botón «Quitar la pestaña» oculto (aria-hidden, fuera del Tab) que solo trae un `title` en inglés
// («Remove  tab») y ningún nombre propio: una revisión automática lo cuenta como botón sin nombre (3 en el Visor, uno por
// hoja; 2 en Administración, uno por forma de agregar una carpeta). Aquí se exige que todo botón de una lista de
// pestañas, oculto o no, se encuentre por rol y nombre en español y que no quede el texto en inglés.
import { Tab, Tabs } from "@carbon/react";
import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { Entrar } from "../sesion/Entrar";
import { TabList } from "./carbonEs";

function Hojas({ nombres }: { nombres: string[] }) {
  return (
    <Tabs>
      <TabList aria-label="Hojas del libro" contained>
        {nombres.map((n) => (
          <Tab key={n}>{n}</Tab>
        ))}
      </TabList>
    </Tabs>
  );
}

describe("botones sin nombre accesible (D10)", () => {
  test("cada pestaña trae su botón oculto con nombre en español, hallable por rol y nombre", () => {
    render(<Hojas nombres={["PORTADA", "PLAN DE PAGOS", "AUX"]} />);
    for (const hoja of ["PORTADA", "PLAN DE PAGOS", "AUX"]) {
      expect(screen.getByRole("button", { hidden: true, name: `Quitar la pestaña ${hoja}` })).toBeInTheDocument();
    }
  });

  test("ningún botón de la lista de pestañas queda sin nombre ni con el título en inglés", () => {
    const { container } = render(<Hojas nombres={["Una", "Otra"]} />);
    const botones = [...container.querySelectorAll("button")];
    expect(botones.length).toBeGreaterThanOrEqual(4);
    for (const b of botones) {
      expect(b.getAttribute("aria-label") || b.textContent?.trim(), b.outerHTML.slice(0, 120)).toBeTruthy();
      expect(b.getAttribute("title") ?? "").not.toMatch(/Remove|tab\b/);
    }
  });

  test("las pestañas que aparecen después también reciben el nombre", () => {
    const { rerender } = render(<Hojas nombres={["Una"]} />);
    rerender(<Hojas nombres={["Una", "Nueva"]} />);
    expect(screen.getByRole("button", { hidden: true, name: "Quitar la pestaña Nueva" })).toBeInTheDocument();
  });

  test("«Entrar»: el control de la contraseña se encuentra por rol y nombre", () => {
    render(<Entrar onEntrar={vi.fn()} />);
    expect(screen.getByRole("button", { name: "Mostrar la contraseña" })).toBeInTheDocument();
  });
});
