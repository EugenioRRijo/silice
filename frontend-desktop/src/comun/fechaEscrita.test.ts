import { describe, expect, test } from "vitest";
import { anteriorA, hoyIso, leerFechaEscrita } from "./fechaEscrita";

// Oráculos a mano: la fecha se escribe como se lee (dd/mm/aaaa) y viaja como la espera la API (aaaa-mm-dd).
describe("leerFechaEscrita", () => {
  test("vacía es «sin fecha»", () => {
    expect(leerFechaEscrita("")).toEqual({ ok: true, iso: null });
    expect(leerFechaEscrita("   ")).toEqual({ ok: true, iso: null });
  });

  test("dd/mm/aaaa, con o sin ceros, viaja como aaaa-mm-dd", () => {
    expect(leerFechaEscrita("15/12/2026")).toEqual({ ok: true, iso: "2026-12-15" });
    expect(leerFechaEscrita(" 5/1/2027 ")).toEqual({ ok: true, iso: "2027-01-05" });
    expect(leerFechaEscrita("29/02/2028")).toEqual({ ok: true, iso: "2028-02-29" });
  });

  test("otra forma pide dd/mm/aaaa", () => {
    for (const escrito of ["2026-12-15", "15-12-2026", "15/12/26", "mañana", "15/12/2026 10:00"]) {
      expect(leerFechaEscrita(escrito)).toEqual({ ok: false, error: "Escriba la fecha como dd/mm/aaaa." });
    }
  });

  test("un día que no existe no se corre al mes siguiente", () => {
    for (const escrito of ["31/02/2026", "29/02/2026", "99/99/2026", "00/12/2026", "31/04/2026", "15/13/2026"]) {
      expect(leerFechaEscrita(escrito)).toEqual({ ok: false, error: "La fecha escrita no existe en el calendario." });
    }
  });
});

describe("hoyIso y anteriorA", () => {
  test("hoy en la hora local, como aaaa-mm-dd", () => {
    expect(hoyIso(new Date(2026, 10, 27, 23, 59))).toBe("2026-11-27");
    expect(hoyIso(new Date(2027, 0, 5, 0, 0))).toBe("2027-01-05");
  });

  test("solo un día anterior cuenta como pasado: hoy no", () => {
    expect(anteriorA("2026-11-26", "2026-11-27")).toBe(true);
    expect(anteriorA("2026-11-27", "2026-11-27")).toBe(false);
    expect(anteriorA("2026-12-01", "2026-11-27")).toBe(false);
  });
});
