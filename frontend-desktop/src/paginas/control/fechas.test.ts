import { describe, expect, test } from "vitest";
import { feriadosParaEnviar, fechasEsVe } from "./fechas";

describe("fechas de Control y Reajuste (VB-19)", () => {
  test("fechasEsVe cambia cada fecha ISO de un texto a dd/mm/aaaa y deja el resto igual", () => {
    expect(fechasEsVe("2026-11-02 a 2026-11-06")).toBe("02/11/2026 a 06/11/2026");
    expect(fechasEsVe("2026-11-09 09:00")).toBe("09/11/2026 09:00");
    expect(fechasEsVe("dia 12 (2026-11-18)")).toBe("dia 12 (18/11/2026)");
    expect(fechasEsVe("versión OB-001, vigente desde 2026-11-02; inicio de obra 2026-11-02")).toBe(
      "versión OB-001, vigente desde 02/11/2026; inicio de obra 02/11/2026",
    );
    expect(fechasEsVe("el periodo 2027-02-01–2027-03-31 cruza")).toBe("el periodo 01/02/2027–31/03/2027 cruza");
    // lo que no es una fecha (un codigo, una cifra) no se toca
    expect(fechasEsVe("V-01 4358.20 OB-2026-11")).toBe("V-01 4358.20 OB-2026-11");
    expect(fechasEsVe("")).toBe("");
  });

  test("los feriados se escriben en dd/mm/aaaa y se mandan en AAAA-MM-DD", () => {
    expect(feriadosParaEnviar("25/12/2026, 01/01/2027")).toBe("2026-12-25, 2027-01-01");
    expect(feriadosParaEnviar("2026-12-25,\n1/1/2027")).toBe("2026-12-25,\n2027-01-01");
    // lo que no parece fecha pasa tal cual y la API dice que esta mal
    expect(feriadosParaEnviar("navidad")).toBe("navidad");
    expect(feriadosParaEnviar("")).toBe("");
  });
});
