import { describe, expect, test } from "vitest";
import { centesimasEsVe, fechaEsVe, formatoEsVe, formatoMontoEsVe } from "./formatoEsVe";

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

// Oraculos a mano: redondeo «mitad hacia arriba» en valor absoluto (el de Entregar, V-13) y los totales del
// Historial que vio la auditoria visual (VB-7): 4.876,56257 y 5.055,521570000.
describe("centesimasEsVe (VB-7)", () => {
  test.each([
    ["4876.56257", "4.876,56"],
    ["5055.521570000", "5.055,52"],
    ["1234567.891000", "1.234.567,89"],
    ["1234500.5", "1.234.500,50"],
    ["0", "0,00"],
    ["0.005", "0,01"],
    ["0.004999", "0,00"],
    ["999.995", "1.000,00"],
    ["-1234.5", "-1.234,50"],
    ["-0.004", "0,00"],
    ["-0.005", "-0,01"],
    ["12345678901234567890.125", "12.345.678.901.234.567.890,13"],
  ])("%s se lee %s", (exacto, esperado) => {
    expect(centesimasEsVe(exacto)).toBe(esperado);
  });

  test("lo que no es un decimal llega tal cual", () => {
    expect(centesimasEsVe("n/d")).toBe("n/d");
    expect(centesimasEsVe("")).toBe("");
  });
});

describe("fechaEsVe (VB-19)", () => {
  test("una fecha ISO se lee dd/mm/aaaa", () => {
    expect(fechaEsVe("2026-11-02")).toBe("02/11/2026");
    expect(fechaEsVe("2026-07-31")).toBe("31/07/2026");
  });
  test("con hora, se lee dd/mm/aaaa hh:mm (sin segundos)", () => {
    expect(fechaEsVe("2026-10-18T14:32:05")).toBe("18/10/2026 14:32");
  });
  test("lo que no es una fecha ISO se devuelve tal cual", () => {
    expect(fechaEsVe("ayer")).toBe("ayer");
    expect(fechaEsVe("")).toBe("");
    expect(fechaEsVe("02/11/2026")).toBe("02/11/2026");
  });
});
