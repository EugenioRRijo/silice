import { describe, expect, test } from "vitest";
import { vistaApu } from "./datosDePrueba";
import { mensajeDeRechazo } from "./logica";
import {
  FRASE_DE_APU,
  LIMITE_DE_INSUMOS,
  TIPOS_DE_LINEA,
  cambiarCantidadDeLinea,
  cambiarDesperdicioDeLinea,
  cambiarRendimiento,
  conLineaAgregada,
  conLineaQuitada,
  cuerpoDeApu,
  cuerpoDeInsumo,
  insumosVisibles,
  rutaDeApu,
  rutaDeInsumo,
  rutaDeInsumos,
  sembrarApu,
  estadosDeLaPartida,
  textoDeEstado,
  ubicarErrorDeApu,
} from "./logicaApu";

// Lógica pura de la edición del APU y del cambio de insumo (3c-3: E6, E7, E8 del diseño §4.4). Los valores esperados
// están escritos a mano desde el contrato y desde los mensajes de la clásica (ui/hoja.py:937-985, 1002-1056); ninguno
// sale del código bajo prueba. Todo viaja como texto: aquí no se convierte nada a número.
const ID = "id-borrador-aaaaaaaaaaaa";

describe("rutas del APU", () => {
  test("E6 y E7 cuelgan del borrador y de la partida; el código de partida se codifica (puede traer «/»)", () => {
    expect(rutaDeApu(ID, "AF-LLAVE")).toBe(`/v1/hoja/borradores/${ID}/apu/AF-LLAVE`);
    expect(rutaDeApu(ID, "AF-CODO-1/2")).toBe(`/v1/hoja/borradores/${ID}/apu/AF-CODO-1%2F2`);
    expect(rutaDeInsumo(ID, "AF-CODO-1/2")).toBe(`/v1/hoja/borradores/${ID}/apu/AF-CODO-1%2F2/insumo`);
  });

  test("E8 pide el tipo, el texto (solo si lo hay, sin espacios de las puntas) y el límite 301", () => {
    expect(rutaDeInsumos(ID, "material", "")).toBe(`/v1/hoja/borradores/${ID}/insumos?tipo=material&limite=301`);
    expect(rutaDeInsumos(ID, "mano_obra", "  plomero ")).toBe(
      `/v1/hoja/borradores/${ID}/insumos?tipo=mano_obra&texto=plomero&limite=301`,
    );
    expect(LIMITE_DE_INSUMOS).toBe(300);
  });
});

describe("lo que se edita del APU", () => {
  test("se siembra con el texto exacto que mandó el servidor, por rubro y en orden", () => {
    const detalle = vistaApu().detalle!;
    expect(sembrarApu(detalle)).toEqual({
      rendimiento: "20",
      cantidades: { materiales: ["1"], equipos: ["1"], "mano de obra": ["1", "1"] },
      desperdicios: [""],
    });
  });

  test("en Materiales, la fila con desperdicio siembra su neta como cantidad y su porcentaje en desperdicios", () => {
    const base = vistaApu().detalle!;
    const detalle = {
      ...base,
      grupos: base.grupos.map((g, i) =>
        i === 0
          ? {
              ...g,
              filas: [
                { descripcion: "Arena ficticia", unidad: "m3", cantidad: "1,2", precio: "10" },
                { descripcion: "Ligante ficticio", unidad: "l", cantidad: "0,52", precio: "2,00" },
              ],
            }
          : g,
      ),
      desperdicios: [{ fila: 2, texto: "0,50 + 4 %", neta: "0,50", porcentaje: "4" }],
    };
    expect(sembrarApu(detalle)).toEqual({
      rendimiento: "20",
      cantidades: { materiales: ["1,2", "0,50"], equipos: ["1"], "mano de obra": ["1", "1"] },
      desperdicios: ["", "4"],
    });
  });

  test("cambiar una cantidad toca solo esa línea; cambiar el rendimiento, solo el rendimiento", () => {
    const base = sembrarApu(vistaApu().detalle!);
    const a = cambiarCantidadDeLinea(base, "mano de obra", 1, "2,5");
    expect(a.cantidades).toEqual({ materiales: ["1"], equipos: ["1"], "mano de obra": ["1", "2,5"] });
    expect(a.rendimiento).toBe("20");
    expect(base.cantidades["mano de obra"]).toEqual(["1", "1"]); // no muta lo anterior
    expect(cambiarRendimiento(base, "25").rendimiento).toBe("25");
    expect(cambiarRendimiento(base, "25").cantidades).toEqual(base.cantidades);
  });

  test("el cuerpo de E6 lleva rev, rendimiento, cantidades y desperdicios por línea, tal como se escribieron", () => {
    const sembrado = sembrarApu(vistaApu().detalle!);
    const conNeta = cambiarCantidadDeLinea(sembrado, "materiales", 0, "007e3");
    const conDesp = cambiarDesperdicioDeLinea(conNeta, 0, "4,5");
    const base = cambiarRendimiento(conDesp, "1e1");
    expect(sembrado.desperdicios).toEqual([""]);
    expect(cuerpoDeApu(4, base)).toEqual({
      rev: 4,
      rendimiento: "1e1",
      materiales: ["007e3"],
      equipos: ["1"],
      mano_obra: ["1", "1"],
      desperdicios: ["4,5"],
    });
  });

  test("agregar o quitar una línea de materiales agrega o quita su desperdicio en la misma posición", () => {
    const base = cambiarDesperdicioDeLinea(sembrarApu(vistaApu().detalle!), 0, "4");
    const agregada = conLineaAgregada(base, "materiales", "2");
    expect(agregada.cantidades.materiales).toEqual(["1", "2"]);
    expect(agregada.desperdicios).toEqual(["4", ""]);
    const conSegundo = cambiarDesperdicioDeLinea(agregada, 1, "6");
    const quitada = conLineaQuitada(conSegundo, "materiales", 0);
    expect(quitada.cantidades.materiales).toEqual(["2"]);
    expect(quitada.desperdicios).toEqual(["6"]);
    // En otro rubro los desperdicios de materiales no cambian.
    expect(conLineaAgregada(conSegundo, "equipos", "3").desperdicios).toEqual(["4", "6"]);
    expect(conLineaQuitada(conSegundo, "equipos", 0).desperdicios).toEqual(["4", "6"]);
  });

  test("el cuerpo de E7 lleva rev, tipo, índice desde 0 y el código del insumo", () => {
    expect(cuerpoDeInsumo(2, "mano_obra", 1, "MO-007")).toEqual({ rev: 2, tipo: "mano_obra", indice: 1, insumo: "MO-007" });
  });

  test("los tres tipos de línea de la clásica, con el rubro del APU que les toca", () => {
    expect(TIPOS_DE_LINEA).toEqual([
      { valor: "material", rotulo: "Material", grupo: "materiales" },
      { valor: "equipo", rotulo: "Equipo", grupo: "equipos" },
      { valor: "mano_obra", rotulo: "Mano de obra", grupo: "mano de obra" },
    ]);
  });
});

describe("dónde está el error de un 422", () => {
  test.each([
    [
      "materiales, fila 2: el desperdicio «x» no se entiende como número. Use la coma para los decimales.",
      { campo: "desperdicio", fila: 2 },
    ],
    [
      "materiales, fila 1: el desperdicio «150» debe estar entre 0 y 100 (es un porcentaje: 4 es 4 %).",
      { campo: "desperdicio", fila: 1 },
    ],
    ["materiales, fila 2: la cantidad no puede ser negativa", { campo: "linea", grupo: "materiales", fila: 2 }],
    ["equipos, fila 1: cantidad: 'x' no es un numero decimal valido", { campo: "linea", grupo: "equipos", fila: 1 }],
    ["mano de obra, fila 12: cantidad: 'NaN' no es un monto finito", { campo: "linea", grupo: "mano de obra", fila: 12 }],
    ["rendimiento: 'mucho' no es un numero decimal valido", { campo: "rendimiento" }],
    ["rendimiento debe ser positivo", { campo: "rendimiento" }],
  ])("«%s»", (detalle, esperado) => {
    expect(ubicarErrorDeApu(detalle)).toEqual(esperado);
  });

  test.each([
    "El APU de AF-LLAVE no existe en este borrador",
    "la linea 3 no existe: el grupo material tiene 1 lineas",
    "parametros: utilidad: 'mucho' no es un numero decimal valido",
  ])("un mensaje que no nombra rubro y fila ni rendimiento no se ubica: «%s»", (detalle) => {
    expect(ubicarErrorDeApu(detalle)).toBeNull();
  });

  test("la frase que la clásica agrega tras el error del APU (ui/paginas/hoja.py:1674)", () => {
    expect(FRASE_DE_APU).toBe("La hoja sigue con el último APU válido.");
  });
});

describe("el Estado de la partida", () => {
  test("se muestra solo el texto del estado, sin el «Estado de {clave}: » que arma el servidor", () => {
    expect(textoDeEstado("Estado de AF-CODO-3/4|esp_fuentes:F1: ERROR: fuente F1: falta el origen")).toBe(
      "ERROR: fuente F1: falta el origen",
    );
    expect(textoDeEstado("Estado de AF-SALIDA|esp_puntos:P2: PENDIENTE: sin APU en el catálogo (AF-SALIDA)")).toBe(
      "PENDIENTE: sin APU en el catálogo (AF-SALIDA)",
    );
    expect(textoDeEstado("Estado de AF-LLAVE|esp_puntos:P1: ADVERTENCIA: a; b | ERROR: c")).toBe("ADVERTENCIA: a; b | ERROR: c");
  });

  test("también quita el prefijo cuando el estado es «OK | …» (partida propuesta por la IA)", () => {
    expect(textoDeEstado("Estado de AF-LLAVE|esp_puntos:P1: OK | Propuesta de IA (sesion x)")).toBe("OK | Propuesta de IA (sesion x)");
  });

  test("un texto que no trae el prefijo queda igual", () => {
    expect(textoDeEstado("ERROR: algo")).toBe("ERROR: algo");
  });

  test("E2E-3: la misma partida en tres renglones no repite el mismo aviso tres veces (el servidor lo permuta)", () => {
    // Cada renglón trae primero su propio hallazgo y después los de la partida: el mismo conjunto en otro orden.
    const r1 = (n: number) => `R1 la cantidad del renglón ${n} es manual`;
    expect(
      estadosDeLaPartida([
        `Estado de X-01|1: ADVERTENCIA: ${r1(1)}; ${r1(2)}; ${r1(3)}`,
        `Estado de X-01|2: ADVERTENCIA: ${r1(2)}; ${r1(1)}; ${r1(3)}`,
        `Estado de X-01|3: ADVERTENCIA: ${r1(3)}; ${r1(1)}; ${r1(2)} | ERROR: otro`,
      ]),
    ).toEqual([`ADVERTENCIA: ${r1(1)}; ${r1(2)}; ${r1(3)}`, `ADVERTENCIA: ${r1(3)}; ${r1(1)}; ${r1(2)} | ERROR: otro`]);
  });

  test("E2E-3: estados distintos se conservan, en su orden", () => {
    expect(estadosDeLaPartida(["Estado de A|1: ERROR: a", "Estado de A|2: ADVERTENCIA: b"])).toEqual(["ERROR: a", "ADVERTENCIA: b"]);
  });
});

describe("los candidatos de insumo", () => {
  const insumo = (n: number) => ({ codigo: `MAT-${n}`, descripcion: `Insumo ${n}`, unidad: "u", precio: { texto: "1.00", exacto: "1" } });

  test("con hasta 300 no hay aviso", () => {
    const v = insumosVisibles({ insumos: Array.from({ length: 300 }, (_, i) => insumo(i)), hay_mas: false });
    expect(v.insumos).toHaveLength(300);
    expect(v.hayMas).toBe(false);
  });

  test("con 301 se muestran 300 y se pide acotar (la clásica pide 301 para saberlo)", () => {
    const v = insumosVisibles({ insumos: Array.from({ length: 301 }, (_, i) => insumo(i)), hay_mas: false });
    expect(v.insumos).toHaveLength(300);
    expect(v.insumos[299]!.codigo).toBe("MAT-299");
    expect(v.hayMas).toBe(true);
  });

  test("si el servidor dice que hay más, se pide acotar aunque vengan menos", () => {
    expect(insumosVisibles({ insumos: [insumo(1)], hay_mas: true }).hayMas).toBe(true);
  });
});

describe("el rechazo del cambio de insumo", () => {
  test("la clásica muestra el mensaje solo (ui/paginas/hoja.py:1519): con la frase vacía no se agrega nada", () => {
    expect(mensajeDeRechazo("El insumo MAT-010 no está en la lista de precios de la versión.", "")).toBe(
      "El insumo MAT-010 no está en la lista de precios de la versión.",
    );
    expect(mensajeDeRechazo("sin punto final", "")).toBe("sin punto final");
  });

  test("con frase sigue agregándola tras quitar el punto final", () => {
    expect(mensajeDeRechazo("fila 1: mal.", FRASE_DE_APU)).toBe("fila 1: mal. La hoja sigue con el último APU válido.");
  });
});
