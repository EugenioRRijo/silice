import { render, screen } from "@testing-library/react";
import { describe, expect, test, vi } from "vitest";
import { aplicarTrazos, CurvaPlanAvance, filasDeGrafico, periodos } from "./CurvaPlanAvance";
import type { SerieDeCurva } from "./CurvaPlanAvance";

vi.mock("./GraficoCarbon", () => ({
  default: ({ tipo, datos }: { tipo: string; datos: unknown[] }) => (
    <div data-testid="grafico" data-tipo={tipo} data-filas={datos.length} />
  ),
}));

const SERIES: SerieDeCurva[] = [
  { nombre: "PV", rol: "plan", puntos: [{ periodo: "M1", valor: "1000.00" }, { periodo: "M2", valor: "2500.50" }] },
  { nombre: "EV", rol: "real", puntos: [{ periodo: "M1", valor: "800.00" }] },
  { nombre: "EAC", rol: "pronostico", puntos: [{ periodo: "M2", valor: "2600.00" }] },
];

describe("CurvaPlanAvance", () => {
  test("pasa al grafico una fila por punto, con el valor como numero", () => {
    expect(filasDeGrafico(SERIES)).toHaveLength(4);
    expect(filasDeGrafico(SERIES)[1]).toEqual({ group: "PV", key: "M2", value: 2500.5 });
  });

  test("los periodos salen una sola vez y en orden", () => {
    expect(periodos(SERIES)).toEqual(["M1", "M2"]);
  });

  test("dibuja el grafico y deja la tabla con los montos exactos y un guion donde no hay dato", async () => {
    render(<CurvaPlanAvance titulo="Valor ganado" series={SERIES} unidad="USD" />);
    expect(await screen.findByTestId("grafico")).toHaveAttribute("data-tipo", "linea");
    expect(screen.getByRole("table", { name: "Montos de Valor ganado" })).toBeInTheDocument();
    expect(screen.getByText("2500.50")).toBeInTheDocument();
    expect(screen.getAllByText("—")).toHaveLength(2);
    expect(screen.getByText(/EAC: pronostico \(discontinuo\)/)).toBeInTheDocument();
  });

  test("aplica discontinuo solo al pronostico y mas grosor a lo real", () => {
    const raiz = document.createElement("div");
    raiz.innerHTML = '<svg><path class="line"></path><path class="line"></path><path class="line"></path></svg>';
    const trazos = [...raiz.querySelectorAll<SVGPathElement>("path.line")];
    ["PV", "EV", "EAC"].forEach((name, i) => Object.assign(trazos[i]!, { __data__: { name } }));
    aplicarTrazos(raiz, SERIES);
    expect(trazos.map((t) => t.style.strokeDasharray)).toEqual(["none", "none", "6 4"]);
    expect(trazos.map((t) => t.style.strokeWidth)).toEqual(["1.5", "3", "2"]);
  });
});
