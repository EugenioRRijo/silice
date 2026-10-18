import { describe, expect, test } from "vitest";
import { formatearMostrado } from "./formatoNumero";

describe("formatearMostrado", () => {
  test("General deja el numero exacto y quita los ceros sobrantes de la parte decimal", () => {
    expect(formatearMostrado("1738.407", "General")).toBe("1738.407");
    expect(formatearMostrado("100.0", "General")).toBe("100");
    expect(formatearMostrado("0.10", "General")).toBe("0.1");
  });

  test("General no toca el texto, los booleanos ni los codigos con ceros a la izquierda", () => {
    expect(formatearMostrado("Obra ficticia", "General")).toBe("Obra ficticia");
    expect(formatearMostrado("TRUE", "General")).toBe("TRUE");
    expect(formatearMostrado("007", "General")).toBe("007");
  });

  test("#,##0.00 pone miles y dos decimales", () => {
    expect(formatearMostrado("1234.5", "#,##0.00")).toBe("1,234.50");
    expect(formatearMostrado("200", "#,##0.00")).toBe("200.00");
    expect(formatearMostrado("-1234.5", "#,##0.00")).toBe("-1,234.50");
    expect(formatearMostrado("1234567.891", "#,##0.00")).toBe("1,234,567.89");
  });

  test("#,##0 y 0 redondean al entero, de cero hacia afuera, sin pasar por float", () => {
    expect(formatearMostrado("1234567.891", "#,##0")).toBe("1,234,568");
    expect(formatearMostrado("2.5", "0")).toBe("3");
    expect(formatearMostrado("123456789012345678.5", "0")).toBe("123456789012345679");
  });

  test("0.00 redondea la mitad hacia afuera como Excel", () => {
    expect(formatearMostrado("1738.407", "0.00")).toBe("1738.41");
    expect(formatearMostrado("0.125", "0.00")).toBe("0.13");
    expect(formatearMostrado("-2.675", "0.00")).toBe("-2.68");
    expect(formatearMostrado("0", "0.00")).toBe("0.00");
  });

  test("porcentajes multiplican por cien", () => {
    expect(formatearMostrado("0.5", "0%")).toBe("50%");
    expect(formatearMostrado("0.1234", "0.00%")).toBe("12.34%");
  });

  test("fechas ISO con dd/mm/yyyy y yyyy-mm-dd", () => {
    expect(formatearMostrado("2026-10-18", "dd/mm/yyyy")).toBe("18/10/2026");
    expect(formatearMostrado("2026-10-18", "yyyy-mm-dd")).toBe("2026-10-18");
    expect(formatearMostrado("2026-10-18T10:30:00", "dd/mm/yyyy")).toBe("18/10/2026");
  });

  test("el formato corto de fecha de Excel (mm-dd-yy) se muestra dia/mes/anio", () => {
    expect(formatearMostrado("2026-10-18", "mm-dd-yy")).toBe("18/10/2026");
  });

  test("un formato que no se conoce muestra el valor tal como llega", () => {
    expect(formatearMostrado("12.5", "[$$-409]#,##0.00")).toBe("12.5");
    expect(formatearMostrado("12.5", '0.00" m3"')).toBe("12.5");
  });

  test("un texto con formato numerico se queda como texto", () => {
    expect(formatearMostrado("Hito", "#,##0.00")).toBe("Hito");
  });
});
