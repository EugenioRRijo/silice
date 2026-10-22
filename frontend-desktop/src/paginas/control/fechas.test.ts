import { describe, expect, test } from "vitest";
import { fechaDeRanura, leerFeriados } from "./fechas";

describe("fechas de Control y Reajuste (VB-19)", () => {
  test("fechaDeRanura lee en dd/mm/aaaa una fecha ISO real y deja intacto lo demás (ronda 1)", () => {
    expect(fechaDeRanura("2026-11-13")).toBe("13/11/2026");
    expect(fechaDeRanura("2028-02-29")).toBe("29/02/2028");
    for (const intacto of ["1234-56-78", "9999-99-99", "2026-13-01", "2026-02-30", "2027-02-29", "2026-11-13 a", "x2026-11-13", "", "no disponible"]) {
      expect(fechaDeRanura(intacto)).toBe(intacto);
    }
  });

  test("los feriados se escriben en dd/mm/aaaa y se mandan en AAAA-MM-DD (ronda 1, punto 2)", () => {
    expect(leerFeriados("25/12/2026, 01/01/2027")).toEqual({ feriados: "2026-12-25, 2027-01-01" });
    // separadores: coma, punto y coma o salto de línea; los vacíos no cuentan; día y mes de una cifra valen
    expect(leerFeriados("25/12/2026;1/1/2027\n 24/12/2026 ,, ")).toEqual({ feriados: "2026-12-25, 2027-01-01, 2026-12-24" });
    // una fecha ya escrita en AAAA-MM-DD válida pasa igual
    expect(leerFeriados("2026-12-25")).toEqual({ feriados: "2026-12-25" });
    expect(leerFeriados("")).toEqual({ feriados: "" });
    expect(leerFeriados("  ;, \n")).toEqual({ feriados: "" });
  });

  test("un feriado que no es una fecha dd/mm/aaaa real se rechaza en el front, con lo que escribió la persona", () => {
    for (const malo of ["31/02/2026", "12/25/2026", "25-12-2026", "navidad", "2026-02-30", "1234-56-78", "25/12/26"]) {
      expect(leerFeriados(`01/01/2027, ${malo}`)).toEqual({
        error: `Escriba los feriados como dd/mm/aaaa, separados por comas: «${malo}» no es una fecha.`,
      });
    }
  });
});
