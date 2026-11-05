import { describe, expect, test } from "vitest";
import type { SugerenciaDeConsulta } from "../../comun/consulta";
import { TABLA_DE_CONSULTA, valoresAlElegir } from "./autocompletado";

// AC1 (pedido de Eugenio, 2026-10-21) y AC1b: al componer un APU el insumo se elige de una lista guiada. Aquí, la parte
// pura: qué tabla de consulta alimenta cada tabla de insumos y qué columnas se llenan al elegir. El precio es el de la
// lista para armar que manda `GET /v1/consulta/{tabla}` con su moneda; si no es la moneda de la carpeta, no se copia y se
// avisa. Datos ficticios.

const CEMENTO: SugerenciaDeConsulta = {
  valor: "MAT-1",
  etiqueta: "Cemento gris ficticio (MAT-1, saco)",
  fuente: "Catálogo de la carpeta de trabajo: material",
  descripcion: "Cemento gris ficticio",
  unidad: "saco",
  precio: "18.00",
  moneda: "Bs",
  fecha_precio: "2026-07-01",
};

describe("TABLA_DE_CONSULTA", () => {
  test("materiales y equipos salen de «insumos» (el servidor los junta); mano de obra, de «salarios_cct»", () => {
    expect(TABLA_DE_CONSULTA).toEqual({ materiales: "insumos", equipos: "insumos", mano_obra: "salarios_cct" });
  });
});

describe("valoresAlElegir: la misma moneda", () => {
  test("materiales: descripción, unidad y precio de la lista para armar, este último con coma decimal", () => {
    expect(valoresAlElegir("materiales", CEMENTO, "Bs")).toEqual({
      valores: { descripcion: "Cemento gris ficticio", unidad: "saco", precio: "18,00" },
      aviso: null,
    });
  });

  test("el precio lleva punto de miles y conserva sus decimales tal como los manda la API", () => {
    expect(valoresAlElegir("materiales", { ...CEMENTO, precio: "2000" }, "Bs").valores.precio).toBe("2.000");
    expect(valoresAlElegir("materiales", { ...CEMENTO, precio: "12.3400" }, "Bs").valores.precio).toBe("12,3400");
  });

  test("equipos: descripción y precio; no hay columna de unidad", () => {
    const mezcladora = { ...CEMENTO, valor: "EQ-1", descripcion: "Mezcladora ficticia", unidad: "h", precio: "7.50" };
    expect(valoresAlElegir("equipos", mezcladora, "Bs")).toEqual({
      valores: { descripcion: "Mezcladora ficticia", precio: "7,50" },
      aviso: null,
    });
  });

  test("mano de obra: el jornal de la lista va al sueldo", () => {
    const albanil = { ...CEMENTO, valor: "MO-1", descripcion: "Albañil ficticio", unidad: null, precio: "12.34" };
    expect(valoresAlElegir("mano_obra", albanil, "Bs")).toEqual({
      valores: { descripcion: "Albañil ficticio", sueldo: "12,34" },
      aviso: null,
    });
  });

  test("sin la moneda de la carpeta (la API no la dio) se confía en la del servidor, que ya la comparó", () => {
    expect(valoresAlElegir("materiales", CEMENTO, null).valores.precio).toBe("18,00");
  });
});

describe("valoresAlElegir: otra moneda", () => {
  test("el servidor no manda precio y sí el aviso: se copian descripción y unidad, y el aviso se dice", () => {
    const enUsd = { ...CEMENTO, precio: null, moneda: "USD", aviso_precio: "El catálogo lo tiene en USD; escriba el precio en Bs." };
    expect(valoresAlElegir("materiales", enUsd, "Bs")).toEqual({
      valores: { descripcion: "Cemento gris ficticio", unidad: "saco" },
      aviso: "El catálogo lo tiene en USD; escriba el precio en Bs.",
    });
  });

  test("un precio en otra moneda que la de la carpeta nunca se copia, aunque llegue", () => {
    expect(valoresAlElegir("materiales", { ...CEMENTO, precio: "0.45", moneda: "USD" }, "Bs")).toEqual({
      valores: { descripcion: "Cemento gris ficticio", unidad: "saco" },
      aviso: "El catálogo lo tiene en USD; escriba el precio en Bs.",
    });
    const albanil = { ...CEMENTO, descripcion: "Albañil ficticio", unidad: null, precio: "8.00", moneda: "USD" };
    expect(valoresAlElegir("mano_obra", albanil, "Bs")).toEqual({
      valores: { descripcion: "Albañil ficticio" },
      aviso: "El catálogo lo tiene en USD; escriba el sueldo en Bs.",
    });
  });

  test("un precio sin moneda no se copia (no se sabe en qué está)", () => {
    expect(valoresAlElegir("materiales", { ...CEMENTO, moneda: null }, "Bs").valores).toEqual({
      descripcion: "Cemento gris ficticio",
      unidad: "saco",
    });
  });
});

describe("valoresAlElegir: sin precio", () => {
  test("sin lista para armar (o sin fecha) solo hay descripción y unidad", () => {
    const sinPrecio = { ...CEMENTO, precio: undefined, moneda: undefined, fecha_precio: undefined };
    expect(valoresAlElegir("materiales", sinPrecio, "Bs")).toEqual({
      valores: { descripcion: "Cemento gris ficticio", unidad: "saco" },
      aviso: null,
    });
  });

  test("lo que no viene no se llena ni se inventa", () => {
    const sin = { ...CEMENTO, unidad: null, precio: null };
    expect(valoresAlElegir("materiales", sin, "Bs").valores).toEqual({ descripcion: "Cemento gris ficticio" });
    const vacia = { ...CEMENTO, unidad: "", precio: "" };
    expect(valoresAlElegir("materiales", vacia, "Bs").valores).toEqual({ descripcion: "Cemento gris ficticio" });
  });

  test("la descripción es la que manda el servidor, sin recortar la etiqueta", () => {
    const conParentesis = { ...CEMENTO, etiqueta: "Concreto (f'c 250) en obra (MAT-9)", descripcion: "Concreto (f'c 250) en obra" };
    expect(valoresAlElegir("materiales", conParentesis, "Bs").valores.descripcion).toBe("Concreto (f'c 250) en obra");
  });
});
