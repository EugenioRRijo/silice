import { describe, expect, test } from "vitest";
import { etiquetaDeSubida, extensionesDeSubida, filasDeImportaciones, flujoDelArchivo, rutaDeImportaciones, tipoDeImportacion } from "./logica";
import type { ImportacionesRespuesta } from "./logica";

// Tarea 11 de F4: la lógica pura de Archivos y planos. Los oráculos se escriben a mano: un plano guardado en VIV-002 y
// un cómputo que sigue en el borrador («sin guardar»), con las horas que daría `GET /v1/hoja/importaciones` (Tarea 10).
const REGISTRO: ImportacionesRespuesta = {
  importaciones: [
    {
      tipo: "computo",
      archivo: "movimiento.csv",
      fecha_hora: "2026-11-01T09:30:00",
      usuario: "Ana Pérez <ana>",
      resumen: "18 partidas llevadas",
      version: null,
      guardada: false,
    },
    {
      tipo: "plano",
      archivo: "planta-baja.dxf",
      fecha_hora: "2026-10-31T14:05:09",
      usuario: "Ana Pérez <ana>",
      resumen: "33 filas en el espacio",
      version: "VIV-002",
      guardada: true,
    },
  ],
};

describe("filasDeImportaciones", () => {
  test("una fila por importación, en el orden del servidor, con la fecha en es-VE y «sin guardar»", () => {
    expect(filasDeImportaciones(REGISTRO)).toEqual([
      {
        id: "importacion-0",
        nombre: "movimiento.csv",
        tipo: "Cómputo .csv",
        fecha: "01/11/2026 09:30",
        quien: "Ana Pérez <ana>",
        produjo: "18 partidas llevadas",
        version: "sin guardar",
      },
      {
        id: "importacion-1",
        nombre: "planta-baja.dxf",
        tipo: "Plano .dxf",
        fecha: "31/10/2026 14:05",
        quien: "Ana Pérez <ana>",
        produjo: "33 filas en el espacio",
        version: "VIV-002",
      },
    ]);
  });

  test("un registro vacío no da filas", () => {
    expect(filasDeImportaciones({ importaciones: [] })).toEqual([]);
  });
});

describe("tipoDeImportacion", () => {
  test("el tipo con la extensión del archivo, en minúscula", () => {
    expect(tipoDeImportacion("plano", "OF001.DXF")).toBe("Plano .dxf");
    expect(tipoDeImportacion("plano", "edificio.ifc")).toBe("Plano .ifc");
    expect(tipoDeImportacion("computo", "Computo.Csv")).toBe("Cómputo .csv");
  });

  test("sin una extensión conocida, solo el tipo (el servidor anota «plano» si el nombre no se podía mostrar)", () => {
    expect(tipoDeImportacion("plano", "plano")).toBe("Plano");
    expect(tipoDeImportacion("computo", "datos.txt")).toBe("Cómputo");
  });
});

describe("flujoDelArchivo", () => {
  test(".dxf y .ifc van al plano, .csv al cómputo, sin mirar mayúsculas", () => {
    expect(flujoDelArchivo("of001.dxf")).toBe("plano");
    expect(flujoDelArchivo("EDIFICIO.IFC")).toBe("plano");
    expect(flujoDelArchivo("computo.CSV")).toBe("computo");
  });

  test("otra extensión no tiene flujo", () => {
    expect(flujoDelArchivo("libro.xlsx")).toBeNull();
    expect(flujoDelArchivo("dxf")).toBeNull();
    expect(flujoDelArchivo("plano.dxf.exe")).toBeNull();
  });
});

describe("lo que acepta la subida", () => {
  test("sin el flujo del cómputo (Tarea 12), solo planos", () => {
    expect(extensionesDeSubida(false)).toEqual([".dxf", ".ifc"]);
    expect(etiquetaDeSubida(false)).toBe("Suelte aquí el plano .dxf o .ifc, o haga clic para elegirlo");
  });

  test("con el cómputo, también .csv", () => {
    expect(extensionesDeSubida(true)).toEqual([".dxf", ".ifc", ".csv"]);
    expect(etiquetaDeSubida(true)).toBe("Suelte aquí el plano .dxf o .ifc, o el cómputo .csv, o haga clic para elegirlo");
  });
});

test("la ruta del registro lleva la obra en la consulta", () => {
  expect(rutaDeImportaciones("7")).toBe("/v1/hoja/importaciones?proyecto=7");
  expect(rutaDeImportaciones("Casa Demo")).toBe("/v1/hoja/importaciones?proyecto=Casa%20Demo");
});
