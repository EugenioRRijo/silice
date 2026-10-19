import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { IndicadorFiori } from "./IndicadorFiori";
import type { IndicadorRespuesta } from "./tipos";

function indicador(extra: Partial<IndicadorRespuesta> = {}): IndicadorRespuesta {
  return {
    clave: "total",
    titulo: "Total del libro",
    actual: "1738.407",
    meta: "1500.00",
    delta: "238.407",
    delta_pct: "15.89",
    sentido: "costo",
    ...extra,
  };
}

describe("IndicadorFiori", () => {
  test("el rótulo de la cifra de comparación es «Meta» por omisión y se puede nombrar", () => {
    const { rerender } = render(<IndicadorFiori indicador={indicador()} />);
    expect(screen.getByText(/^Meta/)).toBeInTheDocument();
    rerender(<IndicadorFiori indicador={indicador()} rotuloMeta="Según Sílice" />);
    expect(screen.getByText(/^Según Sílice/)).toBeInTheDocument();
    expect(screen.queryByText(/^Meta/)).not.toBeInTheDocument();
  });

  test("muestra los montos exactos como llegan, sin redondear", () => {
    render(<IndicadorFiori indicador={indicador()} />);
    expect(screen.getByText("1738.407")).toBeInTheDocument();
    expect(screen.getByText("1500.00")).toBeInTheDocument();
    expect(screen.getByText(/238\.407/)).toBeInTheDocument();
  });

  test("con delta_pct nulo no se muestra el signo de porcentaje", () => {
    const { container } = render(<IndicadorFiori indicador={indicador({ delta_pct: null })} />);
    expect(container.textContent).not.toContain("%");
  });

  test("con delta_pct presente se muestra con porcentaje", () => {
    render(<IndicadorFiori indicador={indicador()} />);
    expect(screen.getByText(/15\.89 %/)).toBeInTheDocument();
  });

  test("costo positivo es desfavorable: clase ibcs-desfavorable y texto accesible", () => {
    const { container } = render(<IndicadorFiori indicador={indicador()} />);
    expect(container.querySelector(".ibcs-desfavorable")).not.toBeNull();
    expect(container.querySelector(".ibcs-favorable")).toBeNull();
    expect(screen.getByText("desfavorable")).toBeInTheDocument();
  });

  test("costo negativo es favorable aunque el signo sea menos", () => {
    const { container } = render(
      <IndicadorFiori indicador={indicador({ delta: "-3.10", delta_pct: "-0.2" })} />,
    );
    expect(container.querySelector(".ibcs-favorable")).not.toBeNull();
    expect(screen.getByText("favorable")).toBeInTheDocument();
  });

  test("rendimiento positivo es favorable", () => {
    const { container } = render(
      <IndicadorFiori indicador={indicador({ sentido: "rendimiento", delta: "4", delta_pct: "2" })} />,
    );
    expect(container.querySelector(".ibcs-favorable")).not.toBeNull();
  });

  test("delta cero es neutro y dice sin variacion", () => {
    const { container } = render(
      <IndicadorFiori indicador={indicador({ delta: "0.00", delta_pct: "0.00" })} />,
    );
    expect(container.querySelector(".ibcs-neutro")).not.toBeNull();
    expect(screen.getByText("sin variación")).toBeInTheDocument();
  });

  test("la mini barra marca el real con relleno y la meta con contorno", () => {
    const { container } = render(<IndicadorFiori indicador={indicador()} />);
    expect(container.querySelector(".fiori-kpi__barra-real")).not.toBeNull();
    expect(container.querySelector(".fiori-kpi__barra-meta")).not.toBeNull();
  });

  test("montos no numericos no rompen la barra", () => {
    render(<IndicadorFiori indicador={indicador({ actual: "n/d", meta: "0" })} />);
    expect(screen.getByText("n/d")).toBeInTheDocument();
  });

  test("el titulo nombra la region", () => {
    render(<IndicadorFiori indicador={indicador()} />);
    expect(screen.getByRole("group", { name: "Total del libro" })).toBeInTheDocument();
  });
});
