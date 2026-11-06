import { describe, expect, test } from "vitest";
import { MENSAJE_CIFRA } from "../../indicadores/cifraEscrita";
import {
  AVISO_HERRAMIENTA,
  cuerpoDe,
  errorDeSemilla,
  errorDeVariacion,
  filasDeTabla,
  MENSAJE_SEMILLA,
  MENSAJE_TOPE_CARACTERES,
  MENSAJE_TOPE_INSUMOS,
  MENSAJE_VARIACION,
  rechazoDeInsumo,
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

  test("el cuerpo manda la variacion leida con coma decimal, con punto, y los insumos vacios como null", () => {
    expect(cuerpoDe({ semilla: " 42 ", variacion: "5", insumos: [] })).toEqual({
      semilla: 42,
      variacion_max: "5",
      insumos: null,
    });
    expect(cuerpoDe({ semilla: "0", variacion: "2,50", insumos: ["Arena", "Cemento"] })).toEqual({
      semilla: 0,
      variacion_max: "2.50",
      insumos: ["Arena", "Cemento"],
    });
  });

  test("la tabla conserva el precio como texto, sin tocarlo (la columna lo presenta en es-VE)", () => {
    const filas = filasDeTabla([{ tipo: "material", insumo: "Arena", unidad: "m3", precio: "30.00" }]);
    expect(filas).toEqual([{ id: "0", tipo: "material", insumo: "Arena", unidad: "m3", precio: "30.00" }]);
  });

  test("la variacion acepta la coma decimal y el punto de miles entre 0 y 1000", () => {
    for (const buena of ["0", "5", " 2,5 ", "0,0001", "1000", "1.000", "1000,0", "999,999"]) {
      expect(errorDeVariacion(buena), buena).toBeNull();
    }
  });

  test("el mensaje de la variacion dice la regla de la coma", () => {
    expect(MENSAJE_VARIACION).toContain(MENSAJE_CIFRA);
  });

  test("la variacion rechaza vacio, texto, punto decimal, negativos, exponentes y lo que pasa de 1000", () => {
    for (const mala of ["", "  ", "abc", "2.5", "1,234.5", "-1", "-0,5", "+3", "NaN", "Infinity", "1000,01", "1.000,5", "1001", "12.345", "1E+4", "1e3", "1_0"]) {
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
    expect(resumenDeEnvio({ semilla: 7, variacion_max: "2.5", insumos: ["Arena", "Tubo, 4 pulgadas"] })).toBe(
      "semilla 7, variación 2,5 %, insumos: «Arena», «Tubo, 4 pulgadas»",
    );
  });
});

// AC3: los insumos se eligen de la lista uno a uno y viajan como LISTA de descripciones exactas: una con coma entra
// entera (la API ya no la parte) y ninguna se rechaza por llevarla.
describe("insumos elegidos del simulador", () => {
  test("viajan como lista en el orden elegido; sin ninguno, null (= todos)", () => {
    expect(cuerpoDe({ semilla: "1", variacion: "5", insumos: ["Tubo PVC, 4 pulgadas", "Arena lavada"] }).insumos).toEqual([
      "Tubo PVC, 4 pulgadas",
      "Arena lavada",
    ]);
    expect(cuerpoDe({ semilla: "1", variacion: "5", insumos: [] }).insumos).toBeNull();
  });

  test("rechaza al superar el tope de 200 insumos", () => {
    const alLimite = Array.from({ length: 200 }, (_, i) => `Insumo ${i}`);
    expect(rechazoDeInsumo(alLimite, "Insumo 201")).toBe(MENSAJE_TOPE_INSUMOS);
    expect(rechazoDeInsumo(alLimite.slice(0, 199), "Insumo 200")).toBeNull();
  });

  test("rechaza al superar el tope de 20.000 caracteres en total", () => {
    const largo = "a".repeat(19990);
    expect(rechazoDeInsumo([largo], "b".repeat(11))).toBe(MENSAJE_TOPE_CARACTERES);
    expect(rechazoDeInsumo([largo], "b".repeat(10))).toBeNull();
  });

  test("si el insumo ya está en la lista no lo rechaza por tope (lo atiende la selección)", () => {
    const alLimite = Array.from({ length: 200 }, (_, i) => `Insumo ${i}`);
    expect(rechazoDeInsumo(alLimite, "Insumo 0")).toBeNull();
  });
});
