import { describe, expect, test } from "vitest";
import { MENSAJE_CIFRA } from "../../indicadores/cifraEscrita";
import { ahoraLocalISO, hoyISO, leerCantidad, mostrarCantidad, rotuloUnidad } from "./formato";

describe("mostrarCantidad", () => {
  test("pone la coma decimal, el punto de miles y quita los ceros que sobran sin tocar las cifras", () => {
    expect(mostrarCantidad("24.5000")).toBe("24,5");
    expect(mostrarCantidad("20")).toBe("20");
    expect(mostrarCantidad("20.000")).toBe("20");
    expect(mostrarCantidad("0.125")).toBe("0,125");
    expect(mostrarCantidad("-3.20")).toBe("-3,2");
    expect(mostrarCantidad("100")).toBe("100"); // el cero entero no se toca
    expect(mostrarCantidad("1234.500")).toBe("1.234,5");
    expect(mostrarCantidad("-12000")).toBe("-12.000");
  });

  test("no pasa por float: conserva todos los digitos", () => {
    expect(mostrarCantidad("12345678901234567890.123456789000")).toBe("12.345.678.901.234.567.890,123456789");
  });

  test("el cero negativo se muestra como cero y lo que no es decimal queda como llego", () => {
    expect(mostrarCantidad("-0.000")).toBe("0");
    expect(mostrarCantidad("n/d")).toBe("n/d");
    expect(mostrarCantidad("")).toBe("");
  });
});

describe("leerCantidad", () => {
  // Regla de Eugenio (2026-10-25): coma para los decimales, punto para los miles (src/indicadores/cifraEscrita.ts).
  test("lee la coma decimal y el punto de miles y entrega siempre el decimal con punto para la API", () => {
    expect(leerCantidad("24,5", "de la entrada")).toEqual({ valor: "24.5" });
    expect(leerCantidad("  1234  ", "de la entrada")).toEqual({ valor: "1234" });
    expect(leerCantidad("0,25", "de la entrada")).toEqual({ valor: "0.25" });
    expect(leerCantidad("1.234,5", "de la entrada")).toEqual({ valor: "1234.5" });
    expect(leerCantidad("1.000", "de la entrada")).toEqual({ valor: "1000" });
  });

  test("rechaza el punto decimal y lo ambiguo con la regla, sin adivinar", () => {
    for (const malo of ["2.5", "24.5", "1,234.5", "1.2345", "0.12", "1 234"]) {
      expect(leerCantidad(malo, "de la entrada"), malo).toEqual({
        error: `La cantidad de la entrada está mal escrita. ${MENSAJE_CIFRA}`,
      });
    }
  });

  test("pide la cantidad cuando esta vacia", () => {
    expect(leerCantidad("   ", "del despacho")).toEqual({ error: "Escriba la cantidad del despacho." });
  });

  test("rechaza lo que no es un numero, el signo y los exponentes", () => {
    for (const malo of ["abc", "12abc", "-5", "+5", "1e3", "1,2,3", "1..2", ",", "."]) {
      expect(leerCantidad(malo, "de la entrada"), malo).toHaveProperty("error");
    }
    expect(leerCantidad("-5", "de la entrada")).toEqual({
      error: "La cantidad de la entrada debe ser un número mayor que cero.",
    });
  });

  test("el cero se rechaza salvo que se permita (conteo, existencia minima)", () => {
    expect(leerCantidad("0", "de la entrada")).toEqual({
      error: "La cantidad de la entrada debe ser un número mayor que cero.",
    });
    expect(leerCantidad("0,00", "de la entrada")).toHaveProperty("error");
    expect(leerCantidad("0", "del conteo", { permiteCero: true })).toEqual({ valor: "0" });
    expect(leerCantidad("-1", "del conteo", { permiteCero: true })).toEqual({
      error: "La cantidad del conteo debe ser un número, cero o mayor.",
    });
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
