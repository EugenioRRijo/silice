import { describe, expect, test } from "vitest";
import type { HojaVisualRespuesta } from "../api/tipos";
import { columnaDeDescripcion, contextoDeFila, parsearCelda } from "./celdas";

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

describe("contextoDeFila (M1)", () => {
  test("dice la fila de Excel y el texto de su descripcion", () => {
    const hoja = hojaConFila({ B5: "1", D5: "Friso liso en paredes (ficticio)", P5: "15.00" });
    expect(contextoDeFila(hoja, 4, 15)).toBe("Fila 5: Friso liso en paredes (ficticio)");
  });

  test("un texto muy largo se recorta con puntos suspensivos", () => {
    const hoja = hojaConFila({ D5: "x".repeat(120) });
    const texto = contextoDeFila(hoja, 4, 15) ?? "";
    expect(texto.length).toBeLessThanOrEqual(80);
    expect(texto.endsWith("…")).toBe(true);
  });

  test("sin descripcion no hay contexto", () => {
    expect(contextoDeFila(hojaConFila({ B5: "1" }), 4, 15)).toBeNull();
  });
});

function hojaConFila(valores: Record<string, string>, extra: Partial<HojaVisualRespuesta> = {}): HojaVisualRespuesta {
  return {
    nombre: "H",
    visible: true,
    filas: 20,
    columnas: 20,
    anchos: {},
    altos: {},
    ocultas_filas: [],
    ocultas_columnas: [],
    combinadas: [],
    fijas: null,
    celdas: Object.entries(valores).map(([ref, mostrado]) => ({
      ref,
      fila: Number(ref.replace(/[A-Z]+/, "")),
      columna: 0,
      mostrado,
      formula: null,
      estilo: 0,
    })),
    ...extra,
  };
}

describe("columnaDeDescripcion (M1)", () => {
  test("es la columna con el texto mas largo de la fila, a la izquierda de la celda del hallazgo", () => {
    const hoja = hojaConFila({ B5: "1", C5: "E.311.000.001", D5: "Friso liso en paredes (ficticio)", E5: "m2", F5: "10.00", P5: "15.00" });
    // P = columna 15 (base 0); D = 3.
    expect(columnaDeDescripcion(hoja, 4, 15)).toBe(3);
  });

  test("ignora numeros, fechas y las columnas ocultas", () => {
    const hoja = hojaConFila({ B5: "1", C5: "2026-10-18", D5: "Texto muy largo oculto", E5: "Texto corto" }, { ocultas_columnas: [4] });
    expect(columnaDeDescripcion(hoja, 4, 15)).toBe(4);
  });

  test("sin texto a la izquierda de la celda no hay descripcion", () => {
    const hoja = hojaConFila({ B5: "1", C5: "2", P5: "Texto a la derecha" });
    expect(columnaDeDescripcion(hoja, 4, 15)).toBeNull();
    expect(columnaDeDescripcion(hoja, 4, 1)).toBeNull();
  });

  test("una celda de texto en otra fila no cuenta", () => {
    const hoja = hojaConFila({ D6: "Otra fila" });
    expect(columnaDeDescripcion(hoja, 4, 15)).toBeNull();
  });
});
