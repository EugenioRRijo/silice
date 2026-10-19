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
    // Notacion cientifica (lo que da un decimal muy grande o muy chico): con signo en el exponente o con decimales.
    ["1.5e-07", "numero"],
    ["1e+16", "numero"],
    ["-2.5E-10", "numero"],
    ["1.2E15", "numero"],
    ["e+16", "texto"],
    ["1.5e", "texto"],
    ["1.5e+", "texto"],
  ])("%j es %s", (valor, tipo) => {
    expect(tipoDeValor(valor)).toBe(tipo);
  });
});
