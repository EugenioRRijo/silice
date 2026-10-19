import { describe, expect, test } from "vitest";
import { formatoEsVe, formatoMontoEsVe } from "./formatoEsVe";

describe("formatoEsVe", () => {
  test("miles con punto y decimales con coma", () => {
    expect(formatoEsVe("4358.20")).toBe("4.358,20");
    expect(formatoEsVe("1234567.891")).toBe("1.234.567,891");
    expect(formatoEsVe("999.99")).toBe("999,99");
  });

  test("negativos conservan el signo y el cero no lo lleva", () => {
    expect(formatoEsVe("-61.59")).toBe("-61,59");
    expect(formatoEsVe("-1234.5")).toBe("-1.234,5");
    expect(formatoEsVe("0.00")).toBe("0,00");
  });

  test("enteros sin parte decimal", () => {
    expect(formatoEsVe("1500")).toBe("1.500");
    expect(formatoEsVe("0")).toBe("0");
  });

  test("un signo mas explicito se respeta", () => {
    expect(formatoEsVe("+12.5")).toBe("+12,5");
  });

  test("totales de 30 cifras no pierden ni un digito (nada pasa por Number)", () => {
    expect(formatoEsVe("123456789012345678901234567890.12")).toBe("123.456.789.012.345.678.901.234.567.890,12");
  });

  test("lo que no es un decimal se devuelve tal cual", () => {
    expect(formatoEsVe("n/d")).toBe("n/d");
    expect(formatoEsVe("")).toBe("");
    expect(formatoEsVe("1e5")).toBe("1e5");
  });
});

describe("formatoMontoEsVe (V-19)", () => {
  test("da formato es-VE al decimal y conserva la unidad que lo sigue", () => {
    expect(formatoMontoEsVe("95066.60 USD")).toBe("95.066,60 USD");
    expect(formatoMontoEsVe("2258.98 USD")).toBe("2.258,98 USD");
    expect(formatoMontoEsVe("4131.10")).toBe("4.131,10");
    expect(formatoMontoEsVe("-1234.5 Bs")).toBe("-1.234,5 Bs");
  });

  test("lo que ya viene presentado o no es un monto queda igual", () => {
    expect(formatoMontoEsVe("79,0 %")).toBe("79,0 %");
    expect(formatoMontoEsVe("no disponible")).toBe("no disponible");
    expect(formatoMontoEsVe("")).toBe("");
  });

  test("30 cifras no pierden ninguna", () => {
    expect(formatoMontoEsVe("123456789012345678901234567890.12 USD")).toBe(
      "123.456.789.012.345.678.901.234.567.890,12 USD",
    );
  });
});
