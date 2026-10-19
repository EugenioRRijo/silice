import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test } from "vitest";
import { IndicadorFiori } from "./IndicadorFiori";
import type { IndicadorRespuesta } from "./tipos";

function indicador(extra: Partial<IndicadorRespuesta> = {}): IndicadorRespuesta {
  return {
    clave: "TOTALGEN",
    titulo: "Total del libro",
    actual: "1738.41",
    meta: "1500.00",
    delta: "238.41",
    delta_pct: "15.89",
    sentido: "exactitud",
    ...extra,
  };
}

describe("IndicadorFiori", () => {
  test("muestra los montos en es-VE: miles con punto y decimales con coma", () => {
    render(<IndicadorFiori indicador={indicador({ actual: "4358.21", meta: "4419.80", delta: "-61.59" })} />);
    expect(screen.getByText("4.358,21")).toBeInTheDocument();
    expect(screen.getByText("4.419,80")).toBeInTheDocument();
    expect(screen.getByText(/-61,59/)).toBeInTheDocument();
  });

  test("el exacto del libro y de Silice, en es-VE y sin redondear, es la descripcion accesible del valor", () => {
    render(
      <IndicadorFiori
        indicador={indicador({ actual: "4358.21" })}
        exactoLibro="4358.2100000000000000000000000001"
        exactoSilice="4419.80000000000001"
      />,
    );
    const valor = screen.getByRole("button", { name: /4\.358,21/ });
    expect(valor).toHaveAccessibleDescription(/En el libro: 4\.358,2100000000000000000000000001/);
    expect(valor).toHaveAccessibleDescription(/Según Sílice: 4\.419,80000000000001/);
  });

  test("el valor se alcanza con el teclado (Tab), no solo con el raton", async () => {
    const usuario = userEvent.setup();
    render(<IndicadorFiori indicador={indicador()} exactoLibro="1738.41" exactoSilice="1500.00" />);
    await usuario.tab();
    expect(screen.getByRole("button", { name: /1\.738,41/ })).toHaveFocus();
  });

  test("sin exactos el valor no es un boton", () => {
    render(<IndicadorFiori indicador={indicador()} />);
    expect(screen.queryByRole("button")).toBeNull();
  });

  test("con delta_pct nulo no se muestra el signo de porcentaje", () => {
    const { container } = render(<IndicadorFiori indicador={indicador({ delta_pct: null })} />);
    expect(container.textContent).not.toContain("%");
  });

  test("con delta_pct presente se muestra con coma y porcentaje", () => {
    render(<IndicadorFiori indicador={indicador()} />);
    expect(screen.getByText(/15,89 %/)).toBeInTheDocument();
  });

  test("exactitud con delta positivo es desfavorable: clase y texto accesible", () => {
    const { container } = render(<IndicadorFiori indicador={indicador({ delta: "12.50" })} />);
    expect(container.querySelector(".ibcs-desfavorable")).not.toBeNull();
    expect(container.querySelector(".ibcs-favorable")).toBeNull();
    expect(screen.getByText("desfavorable")).toBeInTheDocument();
  });

  test("exactitud con delta negativo tambien es desfavorable", () => {
    const { container } = render(<IndicadorFiori indicador={indicador({ delta: "-3.10", delta_pct: "-0.2" })} />);
    expect(container.querySelector(".ibcs-desfavorable")).not.toBeNull();
    expect(container.querySelector(".ibcs-favorable")).toBeNull();
  });

  test("costo negativo es favorable aunque el signo sea menos", () => {
    const { container } = render(
      <IndicadorFiori indicador={indicador({ sentido: "costo", delta: "-3.10", delta_pct: "-0.2" })} />,
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

  test("delta cero es neutro, dice sin variacion y no lleva flecha", () => {
    const { container } = render(<IndicadorFiori indicador={indicador({ delta: "0.00", delta_pct: "0.00" })} />);
    expect(container.querySelector(".ibcs-neutro")).not.toBeNull();
    expect(screen.getByText("sin variación")).toBeInTheDocument();
    expect(container.querySelector("[data-sentido]")).toBeNull();
  });

  test("la flecha apunta arriba con delta positivo y abajo con negativo (data-sentido)", () => {
    const { container, rerender } = render(<IndicadorFiori indicador={indicador({ delta: "12.50" })} />);
    expect(container.querySelector("[data-sentido]")?.getAttribute("data-sentido")).toBe("sube");
    rerender(<IndicadorFiori indicador={indicador({ delta: "-3.10" })} />);
    expect(container.querySelector("[data-sentido]")?.getAttribute("data-sentido")).toBe("baja");
  });

  test("el texto accesible va en la misma linea que la cifra, sin salto intermedio", () => {
    const { container } = render(<IndicadorFiori indicador={indicador({ delta: "12.50" })} />);
    const linea = container.querySelector(".fiori-kpi__delta-texto") as HTMLElement;
    // La palabra oculta es hija de la misma linea de texto (no un elemento aparte del contenedor flex: eso
    // produce un salto de linea al leer o copiar el texto).
    expect(linea.querySelector(".silice-oculto-en-linea")?.textContent).toBe("desfavorable");
    expect(linea.textContent).toBe("desfavorable Δ 12,50 (15,89 %)");
  });

  test("la mini barra marca el real con relleno y la meta con contorno", () => {
    const { container } = render(<IndicadorFiori indicador={indicador()} />);
    expect(container.querySelector(".fiori-kpi__barra-real")).not.toBeNull();
    expect(container.querySelector(".fiori-kpi__barra-meta")).not.toBeNull();
  });

  test("la mini barra solo se dibuja si la variacion se ve: con menos de 2 % de diferencia se quita (m7)", () => {
    const { container, rerender } = render(<IndicadorFiori indicador={indicador({ actual: "1015", meta: "1000" })} />);
    expect(container.querySelector(".fiori-kpi__barra")).toBeNull();
    rerender(<IndicadorFiori indicador={indicador({ actual: "1050", meta: "1000" })} />);
    expect(container.querySelector(".fiori-kpi__barra")).not.toBeNull();
  });

  test("el valor con exactos no se presenta como un boton con icono: es texto con la clase del valor (B2)", () => {
    const { container } = render(<IndicadorFiori indicador={indicador()} exactoLibro="1" exactoSilice="2" />);
    const valor = container.querySelector("button.fiori-kpi__valor");
    expect(valor).not.toBeNull();
    expect(valor?.querySelector("svg")).toBeNull();
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
