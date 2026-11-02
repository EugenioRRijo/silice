import { describe, expect, test } from "vitest";
import { aPorcentaje, fechaValida, rangoInvertido } from "./porcentaje";

describe("aPorcentaje", () => {
  test("corre la coma dos lugares sin pasar por float ni perder digitos", () => {
    expect(aPorcentaje("0.0625")).toBe("6.25");
    expect(aPorcentaje("0.062500")).toBe("6.2500");
    expect(aPorcentaje("0.123456789012345678")).toBe("12.3456789012345678");
    expect(aPorcentaje("1.5")).toBe("150");
    expect(aPorcentaje("2")).toBe("200");
  });

  test("respeta el signo y los ceros", () => {
    expect(aPorcentaje("-0.1")).toBe("-10");
    expect(aPorcentaje("0")).toBe("0");
    expect(aPorcentaje("0.00")).toBe("0");
    expect(aPorcentaje("0.005")).toBe("0.5");
  });

  test("entiende la notacion cientifica que escribe Decimal", () => {
    expect(aPorcentaje("1E-7")).toBe("0.00001");
    expect(aPorcentaje("-2.5E-3")).toBe("-0.25");
    expect(aPorcentaje("1E+2")).toBe("10000");
  });

  test("lo que no es un decimal queda como llego", () => {
    expect(aPorcentaje("")).toBe("");
    expect(aPorcentaje("n/d")).toBe("n/d");
  });
});

describe("fechaValida", () => {
  test("acepta solo fechas reales en formato ISO", () => {
    expect(fechaValida("2026-02-28")).toBe(true);
    expect(fechaValida("2028-02-29")).toBe(true);
    expect(fechaValida("2026-02-30")).toBe(false);
    expect(fechaValida("2026-13-01")).toBe(false);
    expect(fechaValida("28/02/2026")).toBe(false);
    expect(fechaValida("")).toBe(false);
  });
});

describe("rangoInvertido", () => {
  test("solo es invertido si las dos fechas existen y desde es posterior", () => {
    expect(rangoInvertido("2026-03-01", "2026-02-01")).toBe(true);
    expect(rangoInvertido("2026-02-01", "2026-02-01")).toBe(false);
    expect(rangoInvertido("2026-01-01", "2026-02-01")).toBe(false);
    expect(rangoInvertido("", "2026-02-01")).toBe(false);
    expect(rangoInvertido("2026-03-01", "")).toBe(false);
  });
});
