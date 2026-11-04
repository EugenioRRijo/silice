import { describe, expect, test } from "vitest";
import { esCodigoValido, pareceCodigo } from "./codigo";

// Pulido F5, Tarea 1: el código de una partida tiene forma de código (letras sin tilde, cifras, punto, guion y guion bajo,
// sin espacios, hasta 64, sin empezar por un signo: el PATRON_CODIGO de `api/esquemas_ola2.py` sin el espacio). En
// «Agregar partida», lo escrito se toma como código solo si además lleva alguna cifra: «zanja» es una descripción.
describe("la forma de un código de partida", () => {
  test.each(["E-411", "Z-99", "OBRA-99", "FIC-1", "C-000.000.001", "LB_01", "A", " Z-99 ", "A".repeat(64)])("«%s» es un código", (t) => {
    expect(esCodigoValido(t)).toBe(true);
  });

  test.each(["", "   ", "excavación de zanja", "E 411", "-E411", ".E411", "E/411", "E:411", "Ñ-1", "A".repeat(65)])(
    "«%s» no es un código",
    (t) => {
      expect(esCodigoValido(t)).toBe(false);
    },
  );

  test.each([
    ["Z-99", true],
    ["OBRA-99", true],
    ["C-000.000.001", true],
    ["zanja", false],
    ["Excavacion", false],
    ["excavación de zanja", false],
    ["bloque 15", false],
  ])("en «Agregar partida», «%s» parece un código: %s", (t, esperado) => {
    expect(pareceCodigo(t)).toBe(esperado);
  });
});
