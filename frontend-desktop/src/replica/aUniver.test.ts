// Pruebas de la conversion contrato neutro (base 1, Excel) -> instantanea de Univer (base 0, pixeles).
// Leen el oraculo compartido de la tarea 2.6 (tests/fixtures/replica/libro_minimo.json, escrito a mano a partir de
// ORACULO.md). Los valores esperados de aqui tambien estan escritos a mano, no salen de la funcion bajo prueba.
import { getNumfmtLocaleTag, numfmt } from "@univerjs/core";
import { describe, expect, test } from "vitest";
import oraculo from "../../../tests/fixtures/replica/libro_minimo.json";
import type { EstiloVisualRespuesta, LibroVisualRespuesta } from "../api/tipos";
import { construirHalos } from "../visor/halos";
import { aUniver, pxDeAlto, pxDeAncho } from "./aUniver";
import { aBase0 } from "./coordenadas";
import { serialDeExcel } from "./fechaSerial";

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

describe("aBase0: la unica resta de uno", () => {
  test("la fila 12 de Excel es la 11 de Univer y la columna 1 es la 0", () => {
    expect(aBase0(12)).toBe(11);
    expect(aBase0(1)).toBe(0);
  });
});

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
  test("F12 de PLAN DE PAGOS cae en cellData[11][5] como numero, con la formula en custom", () => {
    const celda = hoja("PLAN DE PAGOS").cellData?.[11]?.[5];
    expect(celda?.v).toBe(200);
    expect(celda?.t).toBe(2);
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

  test("el numero de celdas de cada hoja es el del contrato: no se pierde ni se inventa ninguna", () => {
    for (const h of libro.hojas) {
      const datos = hoja(h.nombre).cellData ?? {};
      const cuenta = Object.values(datos).reduce((n, fila) => n + Object.keys(fila ?? {}).length, 0);
      expect(cuenta).toBe(h.celdas.length);
    }
  });

  // Copiada A MANO de la tabla "Celdas" de tests/fixtures/replica/ORACULO.md: [hoja, ref, fila0, columna0].
  // No se calcula nada: si la conversion se equivoca de base, esta lista lo dice.
  const ORACULO: [string, string, number, number][] = [
    ["PORTADA", "A1", 0, 0],
    ["PORTADA", "A2", 1, 0],
    ["PORTADA", "B2", 1, 1],
    ["PORTADA", "A3", 2, 0],
    ["PORTADA", "B3", 2, 1],
    ["PORTADA", "A4", 3, 0],
    ["PORTADA", "B4", 3, 1],
    ["PLAN DE PAGOS", "A1", 0, 0],
    ["PLAN DE PAGOS", "A2", 1, 0],
    ["PLAN DE PAGOS", "B2", 1, 1],
    ["PLAN DE PAGOS", "D2", 1, 3],
    ["PLAN DE PAGOS", "A3", 2, 0],
    ["PLAN DE PAGOS", "B3", 2, 1],
    ["PLAN DE PAGOS", "D3", 2, 3],
    ["PLAN DE PAGOS", "AA3", 2, 26],
    ["PLAN DE PAGOS", "A5", 4, 0],
    ["PLAN DE PAGOS", "F11", 10, 5],
    ["PLAN DE PAGOS", "F12", 11, 5],
    ["AUX", "A1", 0, 0],
  ];

  test.each(ORACULO)(
    "%s!%s cae en cellData[%i][%i] y su halo se pide para la misma posicion",
    (nombre, ref, fila0, columna0) => {
      const celda = hoja(nombre).cellData?.[fila0]?.[columna0];
      expect(celda).toBeDefined();
      const dato = libro.hojas.find((h) => h.nombre === nombre)?.celdas.find((c) => c.ref === ref);
      expect(celda?.custom?.mostrado).toBe(dato?.mostrado);

      const { halos } = construirHalos([
        { codigo: "L1", severidad: "ERROR", descripcion: "x", celda: `${nombre}!${ref}`, impacto: null, accion: "x" },
      ]);
      expect(halos[0]).toMatchObject({ hoja: nombre, fila0, columna0 });
    },
  );
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
});

describe("aUniver: valores (RS2-14)", () => {
  test("los numeros van a Univer como numero con el formato del libro como patron", () => {
    const b2 = hoja("PORTADA").cellData?.[1]?.[1];
    expect(b2?.v).toBe(1234.5);
    expect(b2?.t).toBe(2);
    expect(estiloDe(b2)).toMatchObject({ n: { pattern: "#,##0.00" } });
  });

  test("una fecha va como numero de serie de Excel con su patron (2026-10-18 es 46313)", () => {
    const b3 = hoja("PORTADA").cellData?.[2]?.[1];
    expect(b3?.v).toBe(46313);
    expect(b3?.t).toBe(2);
    expect(estiloDe(b3)).toMatchObject({ n: { pattern: "dd/mm/yyyy" } });
  });

  test("un booleano va como booleano", () => {
    const b4 = hoja("PORTADA").cellData?.[3]?.[1];
    expect(b4?.v).toBe(true);
    expect(b4?.t).toBe(3);
  });

  test("el texto va como texto, sin patron, y su valor guardado queda en custom", () => {
    const a2 = hoja("PORTADA").cellData?.[1]?.[0];
    expect(a2?.v).toBe("Monto contratado");
    expect(a2?.t).toBeUndefined();
    expect(estiloDe(a2)?.n).toBeUndefined();
  });

  test("la alineacion por tipo la da Univer (el numero va a la derecha): no se fuerza ht", () => {
    expect(estiloDe(hoja("PORTADA").cellData?.[1]?.[1])?.ht).toBeUndefined();
  });

  test("Univer no recalcula: ninguna celda lleva formula en f", () => {
    for (const id of univer.sheetOrder) {
      for (const fila of Object.values(univer.sheets[id]?.cellData ?? {})) {
        for (const celda of Object.values(fila ?? {})) expect((celda as { f?: unknown } | undefined)?.f).toBeUndefined();
      }
    }
  });

  test("el libro se crea con la localizacion en espanol", () => {
    expect(univer.locale).toBe("esES");
  });
});

// RS2-14: el patron de Excel viaja tal cual y el motor de formatos de Univer lo muestra. Son patrones de formato
// habituales, escritos a mano. Los esperados estan escritos a mano segun Excel con separadores en espanol.
describe("aUniver: patrones habituales de formato (motor de formatos de Univer)", () => {
  const PATRONES: [string, string, string, number, string][] = [
    ["moneda con signo", "\\$#,##0.00", "1234.5", 1234.5, "$1.234,50"],
    ["negativo entre parentesis", "#,##0.00;\\(#,##0.00\\);\\-", "-5", -5, "(5,00)"],
    ["cero como guion", "#,##0.00;\\(#,##0.00\\);\\-", "0", 0, "-"],
    ["porcentaje con una decimal", "0.0%;\\-0.0%;\\-", "0.05", 0.05, "5,0%"],
    ["porcentaje negativo", "0.0%;\\-0.0%;\\-", "-0.05", -0.05, "-5,0%"],
    ["decimales opcionales", "#,##0.##", "1234.5", 1234.5, "1.234,5"],
    ["fecha con mes abreviado", "d-mmm-yy", "2026-10-18", 46313, "18-oct-26"],
    ["fecha con mes en letras", "mmmm", "2026-10-18", 46313, "octubre"],
  ];

  function estiloConPatron(patron: string): EstiloVisualRespuesta {
    return {
      relleno: null,
      fuente: null,
      tamano: null,
      negrita: false,
      cursiva: false,
      subrayado: false,
      color: null,
      alineacion_h: null,
      alineacion_v: null,
      ajustar_texto: false,
      formato_numero: patron,
      bordes: [null, null, null, null],
    };
  }

  function celdaConPatron(patron: string, valor: string) {
    const mini: LibroVisualRespuesta = {
      nombre: "m.xlsx",
      sha256: "0".repeat(64),
      estilos: [estiloConPatron(patron)],
      hojas: [
        {
          nombre: "H",
          visible: true,
          filas: 1,
          columnas: 1,
          anchos: {},
          altos: {},
          ocultas_filas: [],
          ocultas_columnas: [],
          combinadas: [],
          fijas: null,
          celdas: [{ ref: "A1", fila: 1, columna: 1, mostrado: valor, formula: null, estilo: 0 }],
        },
      ],
    };
    const u = aUniver(mini);
    const celda = u.sheets["hoja-0"]?.cellData?.[0]?.[0];
    const s = celda?.s;
    const estilo = typeof s === "string" ? u.styles[s] : s;
    return { celda, patron: (estilo as { n?: { pattern: string } } | undefined)?.n?.pattern };
  }

  test("un numero en notacion cientifica con formato General sale con coma decimal, como lo muestra Excel (N1)", () => {
    for (const [entrada, valor, esperado] of [
      ["1.5e-07", 1.5e-7, "1,5E-07"],
      ["1e+16", 1e16, "1E+16"],
      ["-2.25E-10", -2.25e-10, "-2,25E-10"],
    ] as const) {
      const { celda, patron } = celdaConPatron("General", entrada);
      expect(celda?.v).toBe(valor);
      expect(celda?.t).toBe(2);
      expect(patron).toBeDefined();
      const texto = numfmt.format(patron as string, valor, { locale: getNumfmtLocaleTag("esES" as never), throws: false });
      expect(texto).toBe(esperado);
    }
  });

  test("con un formato propio, la notacion cientifica usa el patron del libro (no el derivado)", () => {
    const { patron } = celdaConPatron("0.00", "1.5e-07");
    expect(patron).toBe("0.00");
  });

  test.each(PATRONES)("%s: %s", (_nombre, patron, entrada, valor, esperado) => {
    const { celda, patron: pasado } = celdaConPatron(patron, entrada);
    expect(pasado).toBe(patron);
    expect(celda?.v).toBe(valor);
    const texto = numfmt.format(patron, celda?.v as number, {
      locale: getNumfmtLocaleTag("esES" as never),
      throws: false,
    });
    expect(texto).toBe(esperado);
  });

  test("General no pasa patron y deja que Univer muestre el numero", () => {
    const { celda, patron } = celdaConPatron("General", "1738.407");
    expect(patron).toBeUndefined();
    expect(celda?.v).toBe(1738.407);
  });

  test("un texto con patron numerico se queda como texto", () => {
    const { celda } = celdaConPatron("#,##0.00", "Hito");
    expect(celda?.v).toBe("Hito");
  });

  test("el formato @ (texto) mantiene como texto incluso lo que parece numero", () => {
    const { celda } = celdaConPatron("@", "100");
    expect(celda?.v).toBe("100");
  });
});

describe("serialDeExcel (sistema 1900)", () => {
  test("2026-10-18 es 46313 (a mano: 46023 es el 1 de enero de 2026 y el 18 de octubre es el dia 291)", () => {
    expect(serialDeExcel("2026-10-18")).toBe(46313);
  });

  test("una hora se vuelve fraccion del dia", () => {
    expect(serialDeExcel("2026-10-18T12:00:00")).toBe(46313.5);
  });

  test("1900-03-01 es 61 y 1900-01-01 es 1 (Excel cuenta un 29 de febrero de 1900 que no existio)", () => {
    expect(serialDeExcel("1900-03-01")).toBe(61);
    expect(serialDeExcel("1900-01-01")).toBe(1);
  });

  test("lo que no es fecha ISO da null", () => {
    expect(serialDeExcel("18/10/2026")).toBeNull();
    expect(serialDeExcel("TRUE")).toBeNull();
  });
});
