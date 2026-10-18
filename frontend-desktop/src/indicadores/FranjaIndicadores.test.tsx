import { render, screen, within } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { FranjaIndicadores } from "./FranjaIndicadores";
import type { IndicadorRespuesta } from "./tipos";

const indicadores: IndicadorRespuesta[] = [
  {
    clave: "total",
    titulo: "Total del libro",
    actual: "1738.407",
    meta: "1500.00",
    delta: "238.407",
    delta_pct: "15.89",
    sentido: "costo",
  },
  {
    clave: "otro",
    titulo: "Otro",
    actual: "10",
    meta: "12",
    delta: "-2",
    delta_pct: null,
    sentido: "costo",
  },
];

const conteos = { CRITICO: 2, ERROR: 0, ADVERTENCIA: 5, INFO: 1 } as const;

describe("FranjaIndicadores", () => {
  test("pinta un indicador por cada elemento de la lista", () => {
    render(<FranjaIndicadores indicadores={indicadores} porSeveridad={conteos} />);
    expect(screen.getByRole("group", { name: "Total del libro" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Otro" })).toBeInTheDocument();
  });

  test("los conteos por severidad llevan texto y numero", () => {
    render(<FranjaIndicadores indicadores={indicadores} porSeveridad={conteos} />);
    const zona = screen.getByRole("group", { name: "Hallazgos por severidad" });
    expect(within(zona).getByText("Crítico")).toBeInTheDocument();
    expect(within(zona).getByText("Error")).toBeInTheDocument();
    expect(within(zona).getByText("Advertencia")).toBeInTheDocument();
    expect(within(zona).getByText("Información")).toBeInTheDocument();
    expect(within(zona).getByText("2")).toBeInTheDocument();
    expect(within(zona).getByText("5")).toBeInTheDocument();
  });

  test("un conteo no usa las clases de variacion IBCS", () => {
    const { container } = render(<FranjaIndicadores indicadores={[]} porSeveridad={conteos} />);
    const zona = container.querySelector(".franja-indicadores__severidad");
    expect(zona).not.toBeNull();
    expect(zona?.querySelector(".ibcs-favorable, .ibcs-desfavorable, .ibcs-neutro")).toBeNull();
  });

  test("sin indicadores aun muestra los conteos", () => {
    render(<FranjaIndicadores indicadores={[]} porSeveridad={conteos} />);
    expect(screen.getByRole("group", { name: "Hallazgos por severidad" })).toBeInTheDocument();
  });
});
