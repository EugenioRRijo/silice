import { render, screen } from "@testing-library/react";
import { describe, expect, test } from "vitest";
import { LineaDeEquivalencia, textoDeEquivalencia } from "./LineaDeEquivalencia";
import type { Equivalencia } from "./LineaDeEquivalencia";

// Tarea D2 (decisiones del 27/10/2026): un precio del corte en otra moneda se convierte con la tasa del BCV y la
// conversion queda a la vista en una linea. Las cifras llegan como texto exacto (punto decimal) y la pantalla solo las
// formatea (coma decimal, punto de miles): no calcula. Oraculos a mano:
//   31,50 USD x 36,50 Bs/USD = 1.149,75 Bs   (31,5 x 36,5 = 1149,75)
//   1.149,75 Bs / 36,50 Bs/USD = 31,50 USD
// El resultado se lee en centesimas (`centesimasEsVe`); el exacto queda en el `title`.

const EN_BS: Equivalencia = {
  precio_original: "31.50",
  moneda_original: "USD",
  tasa: "36.50",
  fecha_tasa: "2026-10-20",
  fuente_tasa: "importacion:3",
  convertido: "1149.75",
  moneda: "Bs",
  operacion: "×",
};
const EN_USD: Equivalencia = {
  precio_original: "1149.75",
  moneda_original: "Bs",
  tasa: "36.50",
  fecha_tasa: "2026-10-20",
  fuente_tasa: "importacion:3",
  convertido: "31.5",
  moneda: "USD",
  operacion: "÷",
};

describe("Línea de equivalencia", () => {
  test("USD a Bs: multiplica por la tasa y lo dice con coma decimal y punto de miles", () => {
    expect(textoDeEquivalencia(EN_BS)).toBe("31,50 USD × 36,50 Bs/USD (BCV del 20/10/2026) = 1.149,75 Bs");
  });

  test("Bs a USD: divide por la tasa", () => {
    expect(textoDeEquivalencia(EN_USD)).toBe("1.149,75 Bs ÷ 36,50 Bs/USD (BCV del 20/10/2026) = 31,50 USD");
  });

  test("la fecha es la de la tasa que se usó, aunque el precio sea de un día posterior", () => {
    const e = { ...EN_BS, fecha_tasa: "2026-10-18" };
    expect(textoDeEquivalencia(e)).toContain("(BCV del 18/10/2026)");
  });

  test("el resultado se lee en centésimas y el exacto queda a un toque, sin perder cifras", () => {
    const e = { ...EN_USD, convertido: "0.0273972602739726027397260274" };
    render(<LineaDeEquivalencia equivalencia={e} />);
    const linea = screen.getByText(/= 0,03 USD/);
    expect(linea).toHaveAttribute("title", expect.stringContaining("0,0273972602739726027397260274 USD"));
    expect(linea).toHaveAttribute("title", expect.stringContaining("importacion:3"));
  });

  test("se pinta como una sola línea de texto", () => {
    render(<LineaDeEquivalencia equivalencia={EN_BS} />);
    expect(screen.getByText("31,50 USD × 36,50 Bs/USD (BCV del 20/10/2026) = 1.149,75 Bs")).toBeInTheDocument();
  });
});
