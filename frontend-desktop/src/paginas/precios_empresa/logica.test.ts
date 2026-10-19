import { describe, expect, test } from "vitest";
import {
  columnasHallazgos,
  etiquetaBase,
  faltaAlgo,
  filasDesconocidos,
  filasHallazgos,
  formularioLista,
  hoyIso,
  rutaHallazgos,
} from "./logica";
import type { DatosLista } from "./logica";

const DATOS: DatosLista = {
  empresa: "Contratista Demo, C.A.",
  rif: "J-00000000-0",
  baseId: "7",
  moneda: "Bs",
  fecha: "2026-09-20",
  fuente: "lista interna",
  nombre: "",
  archivo: new File(["x"], "precios.csv"),
};

describe("logica de Precios de la empresa", () => {
  test("la etiqueta de la base es «nombre (moneda)»", () => {
    expect(etiquetaBase({ id: 1, nombre: "Linea base", moneda: "USD" })).toBe("Linea base (USD)");
  });

  test("hoy en ISO con ceros a la izquierda", () => {
    expect(hoyIso(new Date(2026, 0, 5))).toBe("2026-01-05");
  });

  test("sin moneda o sin archivo falta algo", () => {
    expect(faltaAlgo(DATOS)).toBe(false);
    expect(faltaAlgo({ ...DATOS, moneda: "" })).toBe(true);
    expect(faltaAlgo({ ...DATOS, archivo: null })).toBe(true);
  });

  test("el formulario lleva todos los campos tal como se escribieron", () => {
    const f = formularioLista({ ...DATOS, empresa: "  Con espacios  " });
    expect(f.get("empresa")).toBe("  Con espacios  ");
    expect(f.get("rif")).toBe("J-00000000-0");
    expect(f.get("base_id")).toBe("7");
    expect(f.get("moneda")).toBe("Bs");
    expect(f.get("fecha")).toBe("2026-09-20");
    expect(f.get("fuente")).toBe("lista interna");
    expect(f.get("nombre")).toBe("");
    expect((f.get("archivo") as File).name).toBe("precios.csv");
  });

  test("la ruta de los hallazgos escapa la fecha", () => {
    expect(rutaHallazgos(3, "2026-10-01")).toBe("/v1/precios-empresa/listas/3/hallazgos?fecha=2026-10-01");
    expect(rutaHallazgos(3, "a&b")).toBe("/v1/precios-empresa/listas/3/hallazgos?fecha=a%26b");
  });

  test("las columnas marcan la severidad y el impacto como numerico", () => {
    const columnas = columnasHallazgos(["Regla", "Severidad", "Descripción", "Impacto"]);
    expect(columnas.map((c) => [c.clave, c.celda, c.numerica])).toEqual([
      ["Regla", undefined, undefined],
      ["Severidad", "severidad", undefined],
      ["Descripción", undefined, undefined],
      ["Impacto", undefined, true],
    ]);
  });

  test("las filas llevan un id y conservan el texto exacto", () => {
    const filas = filasHallazgos({
      columnas: ["Regla", "Impacto"],
      filas: [{ Regla: "R11", Impacto: "1057.53" }, { Regla: "R12", Impacto: "" }],
      nota: "",
    });
    expect(filas).toEqual([
      { Regla: "R11", Impacto: "1057.53", id: "0" },
      { Regla: "R12", Impacto: "", id: "1" },
    ]);
    expect(filasDesconocidos(["A", "B"])).toEqual([
      { id: "0", insumo: "A" },
      { id: "1", insumo: "B" },
    ]);
  });
});
