import { describe, expect, test } from "vitest";
import { MONEDAS, monedasDestino, rotuloDeMoneda } from "./monedas";

// D15 de la tanda de detalles: las monedas que maneja Sílice (el nucleo valora en Bs y en USD) tenian tres definiciones en
// paginas y shell. Esta es la unica; la prueba de arquitectura vigila que no vuelvan a aparecer otras.
describe("monedas", () => {
  test("la lista única son los dos códigos que acepta la API, en ese orden", () => {
    expect([...MONEDAS]).toEqual(["Bs", "USD"]);
  });

  test("la moneda destino de una conversión nunca es la actual", () => {
    expect(monedasDestino("Bs")).toEqual(["USD"]);
    expect(monedasDestino("USD")).toEqual(["Bs"]);
    expect(monedasDestino(null)).toEqual(["Bs", "USD"]);
  });

  test("el rótulo corto y el completo de cada moneda", () => {
    expect(rotuloDeMoneda("Bs")).toBe("Bolívares (Bs)");
    expect(rotuloDeMoneda("USD")).toBe("Dólares (USD)");
    expect(rotuloDeMoneda("USD", true)).toBe("Dólares estadounidenses (USD)");
  });
});
