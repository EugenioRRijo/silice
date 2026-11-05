import { describe, expect, test } from "vitest";
import { descripcionDeEtiqueta, TABLA_DE_CONSULTA, valoresAlElegir } from "./autocompletado";
import type { InsumoCatalogo } from "./cliente";

// AC1 (pedido de Eugenio, 2026-10-21): al componer un APU el insumo se elige de una lista guiada. Aquí, la parte pura:
// qué tabla de consulta alimenta cada tabla de insumos y qué columnas se llenan al elegir. Datos ficticios.

const CEMENTO: InsumoCatalogo = {
  codigo: "MAT-1",
  descripcion: "Cemento gris ficticio",
  tipo: "material",
  unidad: "saco",
  precio_vigente: "18.00",
};

describe("TABLA_DE_CONSULTA", () => {
  test("materiales y equipos salen de «insumos» (el servidor los junta); mano de obra, de «salarios_cct»", () => {
    expect(TABLA_DE_CONSULTA).toEqual({ materiales: "insumos", equipos: "insumos", mano_obra: "salarios_cct" });
  });
});

describe("valoresAlElegir", () => {
  test("materiales: descripción, unidad y precio, este último con coma decimal", () => {
    expect(valoresAlElegir("materiales", CEMENTO, "Cemento gris ficticio (MAT-1, saco)", "MAT-1")).toEqual({
      descripcion: "Cemento gris ficticio",
      unidad: "saco",
      precio: "18,00",
    });
  });

  test("el precio lleva punto de miles y conserva sus decimales tal como los manda la API", () => {
    const caro = { ...CEMENTO, precio_vigente: "2000" };
    expect(valoresAlElegir("materiales", caro, "x", "MAT-1").precio).toBe("2.000");
    const fino = { ...CEMENTO, precio_vigente: "12.3400" };
    expect(valoresAlElegir("materiales", fino, "x", "MAT-1").precio).toBe("12,3400");
  });

  test("equipos: descripción y precio; no hay columna de unidad", () => {
    const mezcladora = {
      ...CEMENTO,
      codigo: "EQ-1",
      descripcion: "Mezcladora ficticia",
      tipo: "equipo",
      unidad: "h",
      precio_vigente: "7.50",
    };
    expect(valoresAlElegir("equipos", mezcladora, "x", "EQ-1")).toEqual({
      descripcion: "Mezcladora ficticia",
      precio: "7,50",
    });
  });

  test("mano de obra: el jornal del catálogo va al sueldo", () => {
    const albanil = {
      ...CEMENTO,
      codigo: "MO-1",
      descripcion: "Albañil ficticio",
      tipo: "mano_obra",
      unidad: null,
      precio_vigente: "12.34",
    };
    expect(valoresAlElegir("mano_obra", albanil, "x", "MO-1")).toEqual({
      descripcion: "Albañil ficticio",
      sueldo: "12,34",
    });
  });

  test("lo que el catálogo no trae no se llena ni se inventa", () => {
    const sin = { ...CEMENTO, unidad: null, precio_vigente: null };
    expect(valoresAlElegir("materiales", sin, "x", "MAT-1")).toEqual({ descripcion: "Cemento gris ficticio" });
    const vacia = { ...CEMENTO, unidad: "", precio_vigente: "" };
    expect(valoresAlElegir("materiales", vacia, "x", "MAT-1")).toEqual({ descripcion: "Cemento gris ficticio" });
  });

  test("sin el insumo del catálogo (la lista no cargó) queda solo la descripción, sacada de la etiqueta", () => {
    expect(valoresAlElegir("materiales", null, "Cemento gris ficticio (MAT-1, saco)", "MAT-1")).toEqual({
      descripcion: "Cemento gris ficticio",
    });
  });
});

describe("descripcionDeEtiqueta", () => {
  test("quita el «(código, unidad)» del final cuando es el del insumo", () => {
    expect(descripcionDeEtiqueta("Cemento gris ficticio (MAT-1, saco)", "MAT-1")).toBe("Cemento gris ficticio");
    expect(descripcionDeEtiqueta("Peón ficticio (MO-2)", "MO-2")).toBe("Peón ficticio");
  });

  test("si la etiqueta no termina así, la deja tal cual", () => {
    expect(descripcionDeEtiqueta("Concreto (f'c 250) en obra", "MAT-9")).toBe("Concreto (f'c 250) en obra");
    expect(descripcionDeEtiqueta("Concreto (MAT-9) especial", "MAT-9")).toBe("Concreto (MAT-9) especial");
  });
});
