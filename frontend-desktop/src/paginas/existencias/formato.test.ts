import { describe, expect, test } from "vitest";
import { ahoraLocalISO, hoyISO, leerCantidad, mostrarCantidad, rotuloUnidad } from "./formato";

describe("mostrarCantidad", () => {
  test("pone la coma decimal y quita los ceros que sobran sin tocar las cifras", () => {
    expect(mostrarCantidad("24.5000")).toBe("24,5");
    expect(mostrarCantidad("20")).toBe("20");
    expect(mostrarCantidad("20.000")).toBe("20");
    expect(mostrarCantidad("0.125")).toBe("0,125");
    expect(mostrarCantidad("-3.20")).toBe("-3,2");
    expect(mostrarCantidad("100")).toBe("100"); // el cero entero no se toca
  });

  test("no pasa por float: conserva todos los digitos", () => {
    expect(mostrarCantidad("12345678901234567890.123456789000")).toBe("12345678901234567890,123456789");
  });

  test("el cero negativo se muestra como cero y lo que no es decimal queda como llego", () => {
    expect(mostrarCantidad("-0.000")).toBe("0");
    expect(mostrarCantidad("n/d")).toBe("n/d");
    expect(mostrarCantidad("")).toBe("");
  });
});

describe("leerCantidad", () => {
  test("acepta coma o punto decimal y entrega siempre punto", () => {
    expect(leerCantidad("24,5", "de la entrada")).toEqual({ valor: "24.5" });
    expect(leerCantidad("24.5", "de la entrada")).toEqual({ valor: "24.5" });
    expect(leerCantidad("  1234  ", "de la entrada")).toEqual({ valor: "1234" });
    expect(leerCantidad("0,25", "de la entrada")).toEqual({ valor: "0.25" });
  });

  test("rechaza el separador de miles con una indicacion concreta, sin adivinar", () => {
    expect(leerCantidad("1.234,5", "de la entrada")).toEqual({
      error: "La cantidad de la entrada no debe llevar separador de miles: escriba, por ejemplo, 1234,5.",
    });
    expect(leerCantidad("1,234.5", "de la entrada")).toHaveProperty("error");
  });

  test("pide la cantidad cuando esta vacia", () => {
    expect(leerCantidad("   ", "del despacho")).toEqual({ error: "Escriba la cantidad del despacho." });
  });

  test("rechaza lo que no es un numero, el signo y los exponentes", () => {
    for (const malo of ["abc", "12abc", "-5", "+5", "1e3", "1,2,3", "1..2", ",", "."]) {
      expect(leerCantidad(malo, "de la entrada"), malo).toHaveProperty("error");
    }
  });

  test("el cero se rechaza salvo que se permita (conteo, existencia minima)", () => {
    expect(leerCantidad("0", "de la entrada")).toEqual({
      error: "La cantidad de la entrada debe ser un número mayor que cero.",
    });
    expect(leerCantidad("0,00", "de la entrada")).toHaveProperty("error");
    expect(leerCantidad("0", "del conteo", { permiteCero: true })).toEqual({ valor: "0" });
  });
});

describe("fechas locales", () => {
  test("hoyISO usa el dia local, no el UTC", () => {
    // 23:30 del 17 de octubre, hora local: en UTC ya seria el 18.
    expect(hoyISO(new Date(2026, 9, 17, 23, 30, 0))).toBe("2026-10-17");
    expect(hoyISO(new Date(2026, 0, 5, 0, 5, 0))).toBe("2026-01-05");
  });

  test("ahoraLocalISO es fecha y hora local sin zona", () => {
    expect(ahoraLocalISO(new Date(2026, 9, 18, 9, 5, 7))).toBe("2026-10-18T09:05:07");
  });
});

describe("rotuloUnidad", () => {
  test("m3 se escribe m³ y t queda igual", () => {
    expect(rotuloUnidad("m3")).toBe("m³");
    expect(rotuloUnidad("t")).toBe("t");
    expect(rotuloUnidad("sacos")).toBe("sacos");
  });
});
