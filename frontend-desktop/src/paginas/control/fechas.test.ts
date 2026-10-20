import { describe, expect, test } from "vitest";
import { fechaDeRanura, feriadosParaEnviar } from "./fechas";

describe("fechas de Control y Reajuste (VB-19)", () => {
  test("fechaDeRanura lee en dd/mm/aaaa una fecha ISO real y deja intacto lo demás (ronda 1)", () => {
    expect(fechaDeRanura("2026-11-13")).toBe("13/11/2026");
    expect(fechaDeRanura("2028-02-29")).toBe("29/02/2028");
    for (const intacto of ["1234-56-78", "9999-99-99", "2026-13-01", "2026-02-30", "2027-02-29", "2026-11-13 a", "x2026-11-13", "", "no disponible"]) {
      expect(fechaDeRanura(intacto)).toBe(intacto);
    }
  });

  test("los feriados se escriben en dd/mm/aaaa y se mandan en AAAA-MM-DD", () => {
    expect(feriadosParaEnviar("25/12/2026, 01/01/2027")).toBe("2026-12-25, 2027-01-01");
    expect(feriadosParaEnviar("2026-12-25,\n1/1/2027")).toBe("2026-12-25,\n2027-01-01");
    // lo que no parece fecha pasa tal cual y la API dice que esta mal
    expect(feriadosParaEnviar("navidad")).toBe("navidad");
    expect(feriadosParaEnviar("")).toBe("");
  });
});
