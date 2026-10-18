import { describe, expect, test } from "vitest";
import { cuerpoDe, errorDeSemilla, filasDeTabla, MENSAJE_SEMILLA } from "./logica";

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
});
