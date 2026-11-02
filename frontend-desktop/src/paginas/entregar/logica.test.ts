import { describe, expect, test } from "vitest";
import { textoDeHallazgos, totalPresentado } from "./logica";

describe("totalPresentado (V-13)", () => {
  test.each([
    ["0", "0,00"],
    ["4131.1", "4.131,10"],
    ["1234567.891", "1.234.567,89"],
    ["836.79750000", "836,80"],
    ["0.005", "0,01"],
    ["999.995", "1.000,00"],
    ["-1234.5", "-1.234,50"],
    ["-0.001", "0,00"],
    ["-0.005", "-0,01"],
    ["12345678901234567890.125", "12.345.678.901.234.567.890,13"],
  ])("%s se presenta como %s", (exacto, esperado) => {
    expect(totalPresentado(exacto)).toBe(esperado);
  });

  test("lo que no es un decimal llega tal cual: nunca se esconde ni se altera", () => {
    expect(totalPresentado("n/d")).toBe("n/d");
    expect(totalPresentado("")).toBe("");
  });
});

// VB-16: la cuenta concuerda con el numero («3 advertencias», «1 error») y las severidades se nombran como en el resto
// de la interfaz, en minusculas y con tilde.
describe("textoDeHallazgos (VB-16)", () => {
  test.each([
    [{ ADVERTENCIA: 3 }, "3 advertencias"],
    [{ ADVERTENCIA: 1 }, "1 advertencia"],
    [{ ADVERTENCIA: 2, ERROR: 1 }, "2 advertencias, 1 error"],
    [{ ERROR: 2 }, "2 errores"],
    [{ CRITICO: 1, INFO: 4 }, "1 crítico, 4 informativos"],
    [{ CRITICO: 2, INFO: 1 }, "2 críticos, 1 informativo"],
  ])("%o se lee «%s»", (porSeveridad, esperado) => {
    expect(textoDeHallazgos(porSeveridad)).toBe(esperado);
  });

  test("una severidad que la interfaz no conoce se nombra tal cual llega, en minusculas", () => {
    expect(textoDeHallazgos({ RARA: 2 })).toBe("2 rara");
  });

  test("una severidad con cero no se lista", () => {
    expect(textoDeHallazgos({ ADVERTENCIA: 0, ERROR: 1 })).toBe("1 error");
  });
});
