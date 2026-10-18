// Pruebas de la conversion contrato neutro (base 1, Excel) -> instantanea de Univer (base 0, pixeles).
// Leen el oraculo compartido de la tarea 2.6 (tests/fixtures/replica/libro_minimo.json, escrito a mano a partir de
// ORACULO.md). Los valores esperados de aqui tambien estan escritos a mano, no salen de la funcion bajo prueba.
import { describe, expect, test } from "vitest";
import oraculo from "../../../tests/fixtures/replica/libro_minimo.json";
import type { LibroVisualRespuesta } from "../api/tipos";
import { aUniver, pxDeAlto, pxDeAncho } from "./aUniver";

// El JSON no trae sha256 (depende de los bytes del .xlsx): se rellena con cualquier texto.
const libro = { ...oraculo, sha256: "0".repeat(64) } as unknown as LibroVisualRespuesta;
const univer = aUniver(libro);

function hoja(nombre: string) {
  const entrada = Object.values(univer.sheets).find((h) => h?.name === nombre);
  if (!entrada) throw new Error(`Falta la hoja ${nombre}`);
  return entrada;
}

function estiloDe(celda: { s?: unknown } | undefined | null) {
  const s = celda?.s;
  if (typeof s === "string") return univer.styles[s] ?? undefined;
  return s as Record<string, unknown> | undefined;
}

describe("aUniver: hojas", () => {
  test("las hojas van en el orden del libro y cada una con su nombre", () => {
    const nombres = univer.sheetOrder.map((id) => univer.sheets[id]?.name);
    expect(nombres).toEqual(["PORTADA", "PLAN DE PAGOS", "AUX"]);
  });

  test("la hoja AUX es oculta y las otras dos no", () => {
    expect(hoja("AUX").hidden).toBe(1);
    expect(hoja("PORTADA").hidden).toBe(0);
    expect(hoja("PLAN DE PAGOS").hidden).toBe(0);
  });

  test("el libro lleva el nombre del archivo", () => {
    expect(univer.name).toBe("libro_minimo.xlsx");
  });

  test("hay filas y columnas de sobra para que la hoja llene la pantalla como en Excel", () => {
    expect(hoja("PLAN DE PAGOS").rowCount).toBeGreaterThanOrEqual(12 + 30);
    expect(hoja("PLAN DE PAGOS").columnCount).toBeGreaterThanOrEqual(27 + 10);
  });
});

describe("aUniver: coordenadas (base 1 a base 0)", () => {
  test("F12 de PLAN DE PAGOS cae en cellData[11][5]", () => {
    const celda = hoja("PLAN DE PAGOS").cellData?.[11]?.[5];
    expect(celda?.v).toBe("200.00");
    expect(celda?.custom).toEqual({ mostrado: "200", formula: "=F11*2" });
  });

  test("AA3 cae en cellData[2][26]", () => {
    expect(hoja("PLAN DE PAGOS").cellData?.[2]?.[26]?.v).toBe("Nota lejana");
  });

  test("D3 cae en cellData[2][3] aunque la columna C este oculta", () => {
    expect(hoja("PLAN DE PAGOS").cellData?.[2]?.[3]?.v).toBe("Tras la columna oculta");
  });

  test("A5, en la fila oculta, conserva su fila", () => {
    expect(hoja("PLAN DE PAGOS").cellData?.[4]?.[0]?.v).toBe("Fila oculta");
  });

  test("la celda cubierta por la combinada no existe y la de origen si", () => {
    const fila = hoja("PLAN DE PAGOS").cellData?.[0];
    expect(fila?.[0]?.v).toBe("Plan de pagos ficticio");
    expect(fila?.[1]).toBeUndefined();
  });

  test("ninguna celda del contrato se pierde ni cae en otra posicion", () => {
    for (const h of libro.hojas) {
      const datos = Object.values(univer.sheets).find((x) => x?.name === h.nombre)?.cellData ?? {};
      const cuenta = Object.values(datos).reduce((n, fila) => n + Object.keys(fila ?? {}).length, 0);
      expect(cuenta).toBe(h.celdas.length);
      for (const c of h.celdas) expect(datos[c.fila - 1]?.[c.columna - 1]).toBeDefined();
    }
  });
});

describe("aUniver: combinadas, ocultas y paneles", () => {
  test("A1:D1 se vuelve la combinada de la fila 0, columnas 0 a 3", () => {
    expect(hoja("PLAN DE PAGOS").mergeData).toEqual([{ startRow: 0, startColumn: 0, endRow: 0, endColumn: 3 }]);
  });

  test("la columna 3 (C) oculta es columnData[2].hd = 1 y la fila 5 oculta es rowData[4].hd = 1", () => {
    expect(hoja("PLAN DE PAGOS").columnData?.[2]?.hd).toBe(1);
    expect(hoja("PLAN DE PAGOS").rowData?.[4]?.hd).toBe(1);
  });

  test("la columna oculta conserva su ancho", () => {
    expect(hoja("PLAN DE PAGOS").columnData?.[2]?.w).toBe(89);
  });

  test("B3 como panel fijo congela una columna y dos filas", () => {
    expect(hoja("PLAN DE PAGOS").freeze).toEqual({ xSplit: 1, ySplit: 2, startColumn: 1, startRow: 2 });
  });

  test("sin paneles fijos no hay congelado", () => {
    expect(hoja("PORTADA").freeze).toEqual({ xSplit: 0, ySplit: 0, startColumn: 0, startRow: 0 });
  });
});

describe("aUniver: anchos y altos", () => {
  test("el ancho guardado por Excel (20.7109375) son 145 px", () => {
    // 20 caracteres: trunc((20*7+5)/7*256)/256 = 20.7109375; px = 20.7109375 * 7 = 144.98 = 145.
    expect(pxDeAncho("20.7109375")).toBe(145);
    expect(pxDeAncho("24.7109375")).toBe(173);
    expect(pxDeAncho("14.7109375")).toBe(103);
    expect(pxDeAncho("10.7109375")).toBe(75);
  });

  test("el alto en puntos pasa a pixeles de 96 dpi: 30 pt son 40 px", () => {
    expect(pxDeAlto("30")).toBe(40);
    expect(pxDeAlto("21.75")).toBe(29);
    expect(pxDeAlto("15")).toBe(20);
  });

  test("PLAN DE PAGOS: A=145, F=75, E (sin ancho propio) usa el de la hoja; fila 1 = 40 px", () => {
    const h = hoja("PLAN DE PAGOS");
    expect(h.columnData?.[0]?.w).toBe(145);
    expect(h.columnData?.[5]?.w).toBe(75);
    expect(h.columnData?.[4]?.w).toBeUndefined();
    expect(h.rowData?.[0]?.h).toBe(40);
  });

  test("el ancho y el alto por omision son los de Excel: 64 px y 20 px", () => {
    const h = hoja("PORTADA");
    expect(h.defaultColumnWidth).toBe(64);
    expect(h.defaultRowHeight).toBe(20);
  });
});

describe("aUniver: estilos", () => {
  test("el encabezado combinado tiene relleno, fuente, color, centrado y texto ajustado", () => {
    const e = estiloDe(hoja("PLAN DE PAGOS").cellData?.[0]?.[0]);
    expect(e).toMatchObject({
      bg: { rgb: "#D9E1F2" },
      ff: "Arial",
      fs: 12,
      bl: 1,
      cl: { rgb: "#1F3864" },
      ht: 2,
      vt: 2,
      tb: 3,
    });
  });

  test("el estilo con borde fino en los cuatro lados lo lleva en t, r, b y l", () => {
    const e = estiloDe(hoja("PLAN DE PAGOS").cellData?.[1]?.[0]) as { bd?: Record<string, { s: number }> };
    expect(e.bd?.t?.s).toBe(1);
    expect(e.bd?.r?.s).toBe(1);
    expect(e.bd?.b?.s).toBe(1);
    expect(e.bd?.l?.s).toBe(1);
  });

  test("cursiva, subrayado, rojo, a la derecha y arriba", () => {
    const e = estiloDe(hoja("PLAN DE PAGOS").cellData?.[2]?.[26]);
    expect(e).toMatchObject({ it: 1, ul: { s: 1 }, cl: { rgb: "#C00000" }, ht: 3, vt: 1 });
  });

  test("las celdas con el mismo estilo del contrato comparten el mismo estilo de Univer", () => {
    const a = hoja("PLAN DE PAGOS").cellData?.[1]?.[0]?.s;
    const b = hoja("PLAN DE PAGOS").cellData?.[1]?.[1]?.s;
    expect(a).toBe(b);
  });

  test("un numero con alineacion general se alinea a la derecha, como en Excel", () => {
    expect(estiloDe(hoja("PORTADA").cellData?.[1]?.[1])).toMatchObject({ ht: 3 });
    expect(estiloDe(hoja("PORTADA").cellData?.[1]?.[0])?.ht).toBeUndefined();
  });

  test("un booleano se centra y una fecha va a la derecha", () => {
    expect(estiloDe(hoja("PORTADA").cellData?.[3]?.[1])).toMatchObject({ ht: 2 });
    expect(estiloDe(hoja("PORTADA").cellData?.[2]?.[1])).toMatchObject({ ht: 3 });
  });

  test("el valor mostrado aplica el formato de numero: 1,234.50 y 18/10/2026", () => {
    expect(hoja("PORTADA").cellData?.[1]?.[1]?.v).toBe("1,234.50");
    expect(hoja("PORTADA").cellData?.[2]?.[1]?.v).toBe("18/10/2026");
    expect(hoja("PORTADA").cellData?.[3]?.[1]?.v).toBe("TRUE");
  });

  test("las celdas son siempre texto ya formateado: Univer no recalcula ni reinterpreta", () => {
    const celda = hoja("PLAN DE PAGOS").cellData?.[11]?.[5];
    expect(typeof celda?.v).toBe("string");
    expect(celda?.f).toBeUndefined();
  });
});
