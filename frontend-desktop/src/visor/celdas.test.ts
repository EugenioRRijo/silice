import { describe, expect, test } from "vitest";
import { parsearCelda } from "./celdas";

describe("parsearCelda", () => {
  test("PRESUPUESTO!F12 cae en la fila 11 y la columna 5 (base 0)", () => {
    expect(parsearCelda("PRESUPUESTO!F12")).toEqual({ hoja: "PRESUPUESTO", fila0: 11, columna0: 5 });
  });

  test("APU-01!G48 conserva el guion de la hoja", () => {
    expect(parsearCelda("APU-01!G48")).toEqual({ hoja: "APU-01", fila0: 47, columna0: 6 });
  });

  test("una hoja con espacios y una columna de dos letras", () => {
    expect(parsearCelda("PLAN DE PAGOS!AA3")).toEqual({ hoja: "PLAN DE PAGOS", fila0: 2, columna0: 26 });
  });

  test("separa por el ultimo signo de cierre de exclamacion", () => {
    expect(parsearCelda("A!B!C3")).toEqual({ hoja: "A!B", fila0: 2, columna0: 2 });
  });

  test("una referencia que no es A1 no es una celda", () => {
    expect(parsearCelda("APU-01!Rendimiento")).toBeNull();
  });

  test("vacia, sin hoja o sin referencia da null", () => {
    expect(parsearCelda("")).toBeNull();
    expect(parsearCelda("F12")).toBeNull();
    expect(parsearCelda("PRESUPUESTO!")).toBeNull();
    expect(parsearCelda("!F12")).toBeNull();
  });

  test("tolera los signos $ aunque la API no los manda", () => {
    expect(parsearCelda("PRESUPUESTO!$F$12")).toEqual({ hoja: "PRESUPUESTO", fila0: 11, columna0: 5 });
  });

  test("rechaza lo que se sale de la hoja de Excel (XFD y 1048576)", () => {
    expect(parsearCelda("H!XFD1048576")).toEqual({ hoja: "H", fila0: 1048575, columna0: 16383 });
    expect(parsearCelda("H!XFE1")).toBeNull();
    expect(parsearCelda("H!A0")).toBeNull();
    expect(parsearCelda("H!A1048577")).toBeNull();
  });
});
