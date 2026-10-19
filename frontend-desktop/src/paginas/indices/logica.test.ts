import { describe, expect, test } from "vitest";
import {
  cambiarDefinicion,
  definicionesIniciales,
  faltaXlrd,
  filasRechazos,
  filasSeries,
  formularioConfirmacion,
  formularioLectura,
  hoyIso,
  textoOmitidos,
} from "./logica";
import type { Informe, Lectura } from "./logica";

const INFORME: Informe = {
  archivo: "indices.csv",
  huella: "a".repeat(64),
  fuente: "https://www.bcv.org.ve/x",
  fecha_descarga: "2026-10-11",
  filas_leidas: 4,
  filas_rechazadas: 1,
  provisionales: 1,
  series: [
    { clave: "INDICE-A", valores: 2, desde: "2026-01-01", hasta: "2026-02-01" },
    { clave: "INDICE-B", valores: 1, desde: "2026-01-01", hasta: "2026-01-01" },
  ],
  rechazos: [{ lugar: "indices.csv:4", motivo: "(serie, fecha) repetido" }],
  rechazos_omitidos: 0,
  advertencias: [],
};

function lectura(tipo: string): Lectura {
  return {
    tipo,
    archivo: new File(["x"], "indices.csv"),
    fuente: "https://www.bcv.org.ve/x",
    fechaDescarga: "2026-10-11",
    informe: INFORME,
  };
}

describe("logica de Índices del BCV", () => {
  test("las filas de series y de rechazos son texto tal como llega", () => {
    expect(filasSeries(INFORME.series)[0]).toEqual({
      id: "0-INDICE-A",
      serie: "INDICE-A",
      valores: "2",
      desde: "2026-01-01",
      hasta: "2026-02-01",
    });
    expect(filasRechazos(INFORME.rechazos)).toEqual([
      { id: "0", lugar: "indices.csv:4", motivo: "(serie, fecha) repetido" },
    ]);
  });

  test("el aviso de omitidos concuerda en singular y plural", () => {
    expect(textoOmitidos(1)).toBe("Hay 1 fila rechazada más que no se muestran aquí.");
    expect(textoOmitidos(3)).toBe("Hay 3 filas rechazadas más que no se muestran aquí.");
  });

  test("hoyIso es la fecha local con ceros", () => {
    expect(hoyIso(new Date(2026, 0, 5))).toBe("2026-01-05");
  });

  test("el formulario de lectura lleva tipo, archivo, fuente y fecha", () => {
    const f = formularioLectura(lectura("tasa"));
    expect([...f.keys()]).toEqual(["tipo", "archivo", "fuente", "fecha_descarga"]);
    expect(f.get("tipo")).toBe("tasa");
    expect((f.get("archivo") as File).name).toBe("indices.csv");
    expect(f.get("fecha_descarga")).toBe("2026-10-11");
  });

  test("confirmar reenvía la lectura con su huella y, en un CSV, las definiciones", () => {
    const definiciones = definicionesIniciales(INFORME.series, "indice_bs", ["diaria", "mensual"]);
    const f = formularioConfirmacion(lectura("csv"), definiciones);
    expect(f.get("huella")).toBe("a".repeat(64));
    expect(JSON.parse(String(f.get("definiciones")))).toEqual([
      { serie: "INDICE-A", nombre: "INDICE-A", organismo: "", unidad: "indice_bs", periodicidad: "mensual" },
      { serie: "INDICE-B", nombre: "INDICE-B", organismo: "", unidad: "indice_bs", periodicidad: "mensual" },
    ]);
    expect(String(formularioConfirmacion(lectura("tasa"), definiciones).get("definiciones"))).toBe("[]");
  });

  test("la periodicidad por defecto es mensual, o la primera si no existe", () => {
    expect(definicionesIniciales(INFORME.series, "u", ["anual", "diaria"])[0].periodicidad).toBe("anual");
  });

  test("cambiar una definición no toca las demás ni el original", () => {
    const original = definicionesIniciales(INFORME.series, "u", ["mensual"]);
    const nueva = cambiarDefinicion(original, 1, "organismo", "Ente Demo");
    expect(nueva[1].organismo).toBe("Ente Demo");
    expect(nueva[0]).toBe(original[0]);
    expect(original[1].organismo).toBe("");
  });

  test("falta xlrd solo con un .xls de tasa o INPC en un equipo que no lo lee", () => {
    const xls = new File(["x"], "4_5_7.XLS");
    expect(faltaXlrd("inpc", xls, false)).toBe(true);
    expect(faltaXlrd("inpc", xls, true)).toBe(false);
    expect(faltaXlrd("csv", xls, false)).toBe(false);
    expect(faltaXlrd("tasa", new File(["x"], "t.xlsx"), false)).toBe(false);
    expect(faltaXlrd("tasa", null, false)).toBe(false);
  });
});
