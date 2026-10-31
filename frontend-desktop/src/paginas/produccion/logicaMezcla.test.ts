import { describe, expect, test } from "vitest";
import { consumosDeLaReceta, multiplicar, porcentajeAFraccion, sumaDePorcentajes, ultimoDiaDelMes } from "./logicaMezcla";

// Oráculos a mano, con enteros: ninguno pasa por Number.
describe("multiplicar decimales con punto", () => {
  test.each([
    ["0.94", "2.5", "2.35"],
    ["0.94", "1234.5", "1160.43"],
    ["1", "7", "7"],
    ["0.5", "0.5", "0.25"],
    ["0.10", "10", "1"],
    ["0", "5", "0"],
  ])("%s por %s da %s", (a, b, esperado) => {
    expect(multiplicar(a, b)).toBe(esperado);
  });
});

describe("consumos de una receta", () => {
  const componentes = [
    { codigo: "AGR-12", cantidad_por_t: "0.94", unidad: "t", tipo: "propio" },
    { codigo: "CEM-01", cantidad_por_t: "0.05", unidad: "t", tipo: "comprado" },
    { codigo: "GAS-01", cantidad_por_t: "3", unidad: "l", tipo: "comprado" },
    { codigo: "FIL-02", cantidad_por_t: "0.01", unidad: "t", tipo: "propio" },
  ];
  test("solo los componentes propios salen del inventario", () => {
    expect(consumosDeLaReceta(componentes, "2.5")).toEqual([
      { codigo: "AGR-12", toneladas: "2.35" },
      { codigo: "FIL-02", toneladas: "0.025" },
    ]);
  });
});

describe("porcentajes a fracciones", () => {
  test.each([
    ["75", "0.75"],
    ["25", "0.25"],
    ["100", "1"],
    ["12.5", "0.125"],
    ["0", "0"],
    ["5", "0.05"],
    ["0.5", "0.005"],
  ])("%s %% es %s", (porcentaje, fraccion) => {
    expect(porcentajeAFraccion(porcentaje)).toBe(fraccion);
  });

  test("la suma es exacta", () => {
    expect(sumaDePorcentajes(["33.3", "33.3", "33.4"])).toBe("100");
    expect(sumaDePorcentajes(["70", "20"])).toBe("90");
    expect(sumaDePorcentajes(["0.1", "0.2"])).toBe("0.3");
  });
});

describe("último día del mes", () => {
  test.each([
    ["2026-11", "2026-11-30"],
    ["2026-12", "2026-12-31"],
    ["2026-02", "2026-02-28"],
    ["2028-02", "2028-02-29"],
  ])("%s -> %s", (periodo, dia) => {
    expect(ultimoDiaDelMes(periodo)).toBe(dia);
  });
});
