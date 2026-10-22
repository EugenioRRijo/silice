import { describe, expect, test } from "vitest";
import { semanticaIbcs } from "./ibcs";

describe("semanticaIbcs", () => {
  test("costo: positivo es desfavorable y negativo favorable", () => {
    expect(semanticaIbcs("12.50", "costo")).toBe("desfavorable");
    expect(semanticaIbcs("-3.10", "costo")).toBe("favorable");
  });

  test("exactitud (decision de Eugenio, V-16): el libro mayor que Silice es desfavorable y el libro menor, favorable", () => {
    expect(semanticaIbcs("12.50", "exactitud")).toBe("desfavorable");
    expect(semanticaIbcs("-3.10", "exactitud")).toBe("favorable");
  });

  test.each(["0", "0.00", "-0.00"])("exactitud: el cero %j sigue siendo sin variacion", (cero) => {
    expect(semanticaIbcs(cero, "exactitud")).toBe("neutro");
  });

  test("rendimiento: positivo es favorable y negativo desfavorable", () => {
    expect(semanticaIbcs("4", "rendimiento")).toBe("favorable");
    expect(semanticaIbcs("-4", "rendimiento")).toBe("desfavorable");
  });

  test.each(["0", "0.00", "-0.00", "-0", "0.", ".0", "", "+0.0"])("el cero %j es neutro en los dos sentidos", (cero) => {
    expect(semanticaIbcs(cero, "costo")).toBe("neutro");
    expect(semanticaIbcs(cero, "rendimiento")).toBe("neutro");
  });

  test("un monto muy pequeno pero distinto de cero no es neutro", () => {
    expect(semanticaIbcs("0.001", "costo")).toBe("desfavorable");
    expect(semanticaIbcs("-0.001", "costo")).toBe("favorable");
  });

  test("un signo mas explicito cuenta como positivo", () => {
    expect(semanticaIbcs("+2.5", "costo")).toBe("desfavorable");
  });
});
