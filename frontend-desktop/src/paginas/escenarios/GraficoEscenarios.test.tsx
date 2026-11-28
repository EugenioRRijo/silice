import { render, screen, within } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { GraficoEscenarios } from "./GraficoEscenarios";
import type { EscenarioRespuesta, EscenariosRespuesta } from "./tipos";

// T4 (mutantes de C7b): el gráfico se prueba solo, con el lienzo de Carbon reemplazado por un rótulo que enseña lo que
// recibe, para mirar los datos que se dibujan y no solo los textos que los rodean.
vi.mock("../../comun/GraficoCarbon", () => ({
  default: ({ datos }: { datos: { group?: string; key?: string; value?: number }[] }) => (
    <div role="img" aria-label="Lienzo del gráfico" data-datos={JSON.stringify(datos)} />
  ),
}));

function escenario(nombre: string, total: string, variacion: string, variacionPct: string): EscenarioRespuesta {
  return { nombre, total, variacion, variacion_pct: variacionPct, hallazgos: 0, insumos_variados: 1, partidas: [] };
}

function resultado(escenarios: EscenarioRespuesta[]): EscenariosRespuesta {
  return { codigo_base: "FIC-1", total_base: "1000.00", pendientes_base: [], escenarios };
}

describe("GraficoEscenarios: lo que se dibuja y lo que se lee", () => {
  test("la altura de cada barra es la diferencia con el base y no el total del escenario", async () => {
    render(
      <GraficoEscenarios
        moneda="USD"
        resultado={resultado([
          escenario("Acero baja", "975.00", "-25.00", "-2.50"),
          escenario("Cemento sube", "1120.00", "120.00", "12.00"),
        ])}
      />,
    );
    const lienzo = await screen.findByRole("img", { name: "Lienzo del gráfico" });
    expect(JSON.parse(lienzo.getAttribute("data-datos")!)).toEqual([
      { group: "Acero baja", key: "Acero baja", value: -25 },
      { group: "Cemento sube", key: "Cemento sube", value: 120 },
    ]);
  });

  test("dos escenarios con el mismo nombre se distinguen con su número de orden", async () => {
    render(
      <GraficoEscenarios
        moneda="USD"
        resultado={resultado([
          escenario("Cemento sube", "1050.00", "50.00", "5.00"),
          escenario("Cemento sube", "1100.00", "100.00", "10.00"),
        ])}
      />,
    );
    await screen.findByRole("img", { name: "Lienzo del gráfico" });
    const extremos = screen.getByRole("list", { name: "Diferencia en el extremo de cada escenario" });
    const textos = within(extremos).getAllByRole("listitem").map((li) => li.textContent);
    expect(textos).toEqual(["Cemento sube (1): +50,00 USD (+5,00 %)", "Cemento sube (2): +100,00 USD (+10,00 %)"]);
  });

  test("el mayor cambio es el de mayor magnitud aunque sea una baja", async () => {
    render(
      <GraficoEscenarios
        moneda="USD"
        resultado={resultado([
          escenario("Acero baja mucho", "880.00", "-120.00", "-12.00"),
          escenario("Cemento sube poco", "1050.00", "50.00", "5.00"),
        ])}
      />,
    );
    await screen.findByRole("img", { name: "Lienzo del gráfico" });
    expect(screen.getByText(/el mayor cambio lo produce «Acero baja mucho» con -120,00 USD \(-12,00 %\)/)).toBeInTheDocument();
  });

  test("con una subida y una baja de igual magnitud con signo explícito, manda la mayor sin importar el signo", async () => {
    render(
      <GraficoEscenarios
        moneda="USD"
        resultado={resultado([
          escenario("Sube", "1050.00", "+50.00", "+5.00"),
          escenario("Baja mas", "900.00", "-100.00", "-10.00"),
        ])}
      />,
    );
    await screen.findByRole("img", { name: "Lienzo del gráfico" });
    expect(screen.getByText(/el mayor cambio lo produce «Baja mas»/)).toBeInTheDocument();
  });
});
