import { describe, expect, test } from "vitest";
import { aFilaExcel, columna0ALetras, parsearA1 } from "./coordenadas";

describe("coordenadas", () => {
  test.each([
    [0, "A"],
    [2, "C"],
    [25, "Z"],
    [26, "AA"],
    [51, "AZ"],
    [52, "BA"],
    [16383, "XFD"],
  ])("la columna0 %i es %s", (columna0, letras) => {
    expect(columna0ALetras(columna0)).toBe(letras);
    expect(parsearA1(`${letras}1`)?.columna0).toBe(columna0);
  });

  test("la fila0 11 es la fila 12 de Excel", () => {
    expect(aFilaExcel(11)).toBe(12);
  });
});
