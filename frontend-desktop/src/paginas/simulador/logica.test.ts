import { describe, expect, test } from "vitest";
import {
  AVISO_HERRAMIENTA,
  cuerpoDe,
  errorDeSemilla,
  errorDeVariacion,
  filasDeTabla,
  MENSAJE_SEMILLA,
  MENSAJE_VARIACION,
  resumenDeEnvio,
} from "./logica";

describe("logica del simulador", () => {
  test("la semilla acepta enteros desde 0", () => {
    for (const bueno of ["0", "42", " 7 ", "9007199254740991"]) expect(errorDeSemilla(bueno)).toBeNull();
  });

  test("la semilla rechaza vacio, negativos, decimales, texto y enteros que no caben exactos", () => {
    for (const malo of ["", "  ", "-1", "1.5", "4e2", "abc", "9007199254740993"]) {
      expect(errorDeSemilla(malo)).toBe(MENSAJE_SEMILLA);
    }
  });

  test("el cuerpo manda la variacion como texto y los insumos vacios como null", () => {
    expect(cuerpoDe({ semilla: " 42 ", variacion: "5", insumos: "  " })).toEqual({
      semilla: 42,
      variacion_max: "5",
      insumos: null,
    });
    expect(cuerpoDe({ semilla: "0", variacion: "2.50", insumos: " Arena , Cemento " })).toEqual({
      semilla: 0,
      variacion_max: "2.50",
      insumos: "Arena , Cemento",
    });
  });

  test("la tabla conserva el precio como texto, sin tocarlo", () => {
    const filas = filasDeTabla([{ tipo: "material", insumo: "Arena", unidad: "m3", precio: "30.00" }]);
    expect(filas).toEqual([{ id: "0", tipo: "material", insumo: "Arena", unidad: "m3", precio: "30.00" }]);
  });

  test("la variacion acepta decimales con punto entre 0 y 1000, tambien con exponente", () => {
    for (const buena of ["0", "5", " 2.5 ", "+3", ".5", "5.", "1000", "1E2", "1e+3", "0.0001"]) {
      expect(errorDeVariacion(buena)).toBeNull();
    }
  });

  test("la variacion rechaza vacio, texto, coma decimal, negativos, no finitos y lo que pasa de 1000", () => {
    for (const mala of ["", "  ", "abc", "2,5", "-1", "-0.5", "NaN", "Infinity", "1000.01", "1E+4", "1E+999999", "1_0"]) {
      expect(errorDeVariacion(mala)).toBe(MENSAJE_VARIACION);
    }
  });

  test("el aviso conserva que es herramienta de prueba y no lleva jerga interna", () => {
    expect(AVISO_HERRAMIENTA).toMatch(/herramienta de prueba, no una fuente de mercado/i);
    expect(AVISO_HERRAMIENTA).not.toMatch(/UC-07|I6\.3/);
  });

  test("el resumen de envio nombra los valores enviados", () => {
    expect(resumenDeEnvio({ semilla: 42, variacion_max: "5", insumos: null })).toBe(
      "semilla 42, variación 5 %, insumos: todos",
    );
    expect(resumenDeEnvio({ semilla: 7, variacion_max: "2.5", insumos: "Arena" })).toBe(
      "semilla 7, variación 2.5 %, insumos: Arena",
    );
  });
});
