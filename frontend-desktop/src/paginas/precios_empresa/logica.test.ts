import { describe, expect, test } from "vitest";
import {
  COLUMNAS_ATIPICOS,
  columnasHallazgos,
  etiquetaBase,
  fechaCorta,
  filasAtipicos,
  porcentajeEsVe,
  rutaAtipicos,
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

  // RF-100: el boton «Buscar variaciones atipicas de precio» de la pagina clasica.
  test("la ruta de los atipicos es la de la lista de empresa elegida", () => {
    expect(rutaAtipicos(5)).toBe("/v1/precios-empresa/listas/5/atipicos");
  });

  test("el porcentaje se lee en es-VE sin pasar por Number y conserva sus cifras", () => {
    expect(porcentajeEsVe("0.39")).toBe("0,39 %");
    expect(porcentajeEsVe("-12.50")).toBe("-12,50 %");
    expect(porcentajeEsVe("1234.05")).toBe("1.234,05 %");
    expect(porcentajeEsVe("12345678901234567890.01")).toBe("12.345.678.901.234.567.890,01 %");
  });

  test("la fecha corta es DD/MM/AAAA, como en la pantalla de Streamlit", () => {
    expect(fechaCorta("2026-09-01")).toBe("01/09/2026");
    expect(fechaCorta("no es fecha")).toBe("no es fecha");
  });

  test("las columnas de los atipicos: la variacion es numerica y la severidad lleva su icono", () => {
    expect(COLUMNAS_ATIPICOS.map((c) => [c.clave, c.titulo, c.numerica, c.celda])).toEqual([
      ["insumo", "Insumo", undefined, undefined],
      ["porcentaje", "Variación (en USD)", true, undefined],
      ["desde", "Desde", undefined, undefined],
      ["hasta", "Hasta", undefined, undefined],
      ["severidad", "Severidad", undefined, "severidad"],
    ]);
    const [, porcentaje, desde] = COLUMNAS_ATIPICOS;
    expect(porcentaje.presentar?.("0.39")).toBe("0,39 %");
    expect(desde.presentar?.("2026-09-01")).toBe("01/09/2026");
  });

  test("las filas de los atipicos llevan un id y el texto tal como llega", () => {
    const filas = filasAtipicos({
      disponible: true,
      avisos: [],
      variaciones: [
        {
          insumo: "ATIP-001",
          porcentaje: "0.39",
          desde: "2026-09-01",
          hasta: "2026-10-01",
          severidad: "ADVERTENCIA",
          descripcion: "ATIP-001: variación de 0.39 % entre 2026-09-01 y 2026-10-01 (en USD) se aparta del historial de variaciones del insumo",
        },
      ],
    });
    expect(filas).toEqual([
      { id: "0", insumo: "ATIP-001", porcentaje: "0.39", desde: "2026-09-01", hasta: "2026-10-01", severidad: "ADVERTENCIA" },
    ]);
  });
});
