import { describe, expect, test } from "vitest";
import { totalPresentado } from "./logica";

describe("totalPresentado (V-13)", () => {
  test.each([
    ["0", "0.00"],
    ["4131.1", "4,131.10"],
    ["1234567.891", "1,234,567.89"],
    ["836.79750000", "836.80"],
    ["0.005", "0.01"],
    ["999.995", "1,000.00"],
    ["-1234.5", "-1,234.50"],
    ["-0.001", "0.00"],
    ["-0.005", "-0.01"],
    ["12345678901234567890.125", "12,345,678,901,234,567,890.13"],
  ])("%s se presenta como %s", (exacto, esperado) => {
    expect(totalPresentado(exacto)).toBe(esperado);
  });

  test("lo que no es un decimal llega tal cual: nunca se esconde ni se altera", () => {
    expect(totalPresentado("n/d")).toBe("n/d");
    expect(totalPresentado("")).toBe("");
  });
});
