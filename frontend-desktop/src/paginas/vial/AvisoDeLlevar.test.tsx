import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { AvisoDeLlevar } from "./AvisoDeLlevar";

// Segunda pasada de navegador (31-10): el 409 de «Llevar al presupuesto» salía como unas 20 líneas seguidas, con los códigos
// partidos al borde. El texto es del servidor (tiene pruebas) y no cambia: solo se presenta.
const DETALLE =
  "No se llevó nada: 3 partidas quedarían pendientes en el Presupuesto, sin precio, porque el Presupuesto arma cada APU con la lista «Lista X» de la versión V-1, al 20/09/2026, y con ella no se pueden valorar. " +
  "Insumos sin precio en «Lista X»: «C-000.000.001» («Fresado (ficticio)»); «C-000.000.002» («Costo propio (ficticio)»); «C-000.000.003» («Granzón (ficticio)»). " +
  "Esos precios están en «Lista X» al 31/10/2026. Sin rendimiento registrado al 20/09/2026 o antes: «C-000.000.001», «C-000.000.002», «C-000.000.003». " +
  "Qué hacer: en Componer, guarde esas partidas con fecha 20/09/2026. Luego vuelva a llevar.";

function dibujar(detalle: string) {
  render(<AvisoDeLlevar error={detalle} titulo="No se llevó nada al presupuesto" alCerrar={() => {}} />);
  return screen.getByRole("alert");
}

describe("el aviso del 409 de Llevar", () => {
  test("«Qué hacer» va resaltado y antes del detalle", () => {
    const alerta = dibujar(DETALLE);
    const queHacer = alerta.querySelector(".silice-llevar__que-hacer") as HTMLElement;
    expect(queHacer).not.toBeNull();
    expect(queHacer).toHaveTextContent("Qué hacer: en Componer, guarde esas partidas con fecha 20/09/2026. Luego vuelva a llevar.");
    expect(within(queHacer).getByText("Qué hacer:").tagName).toBe("STRONG");
    const lista = alerta.querySelector("ul") as HTMLElement;
    expect(queHacer.compareDocumentPosition(lista) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  test("los insumos sin precio van en una lista, uno por renglón", () => {
    const alerta = dibujar(DETALLE);
    const items = within(alerta).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent("«C-000.000.001» («Fresado (ficticio)»)");
    expect(items[2]).toHaveTextContent("«C-000.000.003» («Granzón (ficticio)»)");
  });

  test("cada código va en un trozo que no se parte", () => {
    const alerta = dibujar(DETALLE);
    const codigos = Array.from(alerta.querySelectorAll(".silice-codigo-sin-partir")).map((c) => c.textContent);
    expect(codigos).toContain("«C-000.000.001»");
    expect(codigos).toContain("«C-000.000.003»");
    expect(codigos).not.toContain("«Lista X»");
  });

  test("un aviso corto, sin «Qué hacer» ni lista, queda como un solo párrafo con el texto tal cual", () => {
    const corto = "El Presupuesto de la obra tiene abierto un borrador de VIA-001. Guarde o descarte ese borrador y vuelva a llevar.";
    const alerta = dibujar(corto);
    expect(alerta).toHaveTextContent(corto);
    expect(alerta.querySelector("ul")).toBeNull();
    expect(alerta.querySelector(".silice-llevar__que-hacer")).toBeNull();
  });
});

describe("estilos del aviso de Llevar", () => {
  const nodo = (
    globalThis as unknown as {
      process: { cwd(): string; getBuiltinModule(nombre: string): { readFileSync(ruta: string, codificacion: string): string } };
    }
  ).process;
  const scss = nodo.getBuiltinModule("node:fs").readFileSync(`${nodo.cwd()}/src/paginas/vial/vial.scss`, "utf-8");

  test("el código no se parte y «Qué hacer» lleva un borde del tema", () => {
    expect(scss).toMatch(/\.silice-codigo-sin-partir\s*\{[^}]*white-space:\s*nowrap/);
    expect(scss).toMatch(/\.silice-llevar__que-hacer\s*\{[^}]*border-inline-start:[^;]*var\(--cds-support-error\)/);
  });
});
