import { describe, expect, test } from "vitest";
import { iniciales } from "./iniciales";

// Regla: se parte el nombre por espacios (los sobrantes no cuentan). Una sola palabra da su letra; con dos o más, la
// primera letra de la primera palabra y la de la última, en mayúscula, sin las partículas del medio («de la»).
describe("iniciales", () => {
  test.each([
    ["Ana Pérez", "AP"],
    ["Ana", "A"],
    ["  Ana   Pérez  ", "AP"],
    ["María José de la Fuente", "MF"],
    ["ana pérez", "AP"],
    ["Ángel Ñúñez", "ÁÑ"],
    ["Juan Carlos", "JC"],
    ["(Ana) Pérez", "AP"],
    ["", ""],
    ["   ", ""],
    ["--", ""],
  ])("%j da %j", (nombre, esperado) => {
    expect(iniciales(nombre)).toBe(esperado);
  });

  test("una letra fuera del plano básico no se parte en dos", () => {
    expect(iniciales("𝒜na")).toBe("𝒜");
  });
});
