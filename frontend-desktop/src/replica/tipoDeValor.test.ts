import { describe, expect, test } from "vitest";
import { tipoDeValor } from "./tipoDeValor";

describe("tipoDeValor", () => {
  test.each([
    ["1738.407", "numero"],
    ["-5", "numero"],
    ["0", "numero"],
    ["2026-10-18", "fecha"],
    ["2026-10-18T10:30:00", "fecha"],
    ["TRUE", "booleano"],
    ["FALSE", "booleano"],
    ["007", "texto"],
    ["Obra ficticia", "texto"],
    ["", "texto"],
    ["1e5", "texto"],
  ])("%j es %s", (valor, tipo) => {
    expect(tipoDeValor(valor)).toBe(tipo);
  });
});
