import { describe, expect, test } from "vitest";
import { unidadEscrita } from "./unidades";

describe("la unidad se presenta con su exponente", () => {
  test("m2 y m3 se leen m² y m³; lo demás queda igual", () => {
    expect(unidadEscrita("m2")).toBe("m²");
    expect(unidadEscrita("m3")).toBe("m³");
    for (const igual of ["m", "unidad", "t·km", "M2", ""]) expect(unidadEscrita(igual)).toBe(igual);
  });
});
