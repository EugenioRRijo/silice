import { describe, expect, test } from "vitest";
import { vistaApu } from "./datosDePrueba";
import {
  FRASE_DE_APU,
  LIMITE_DE_INSUMOS,
  TIPOS_DE_LINEA,
  cambiarCantidadDeLinea,
  cambiarRendimiento,
  cuerpoDeApu,
  cuerpoDeInsumo,
  insumosVisibles,
  rutaDeApu,
  rutaDeInsumo,
  rutaDeInsumos,
  sembrarApu,
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

  test("el cuerpo de E6 lleva rev, rendimiento y las cantidades por línea, tal como se escribieron", () => {
    const base = cambiarRendimiento(cambiarCantidadDeLinea(sembrarApu(vistaApu().detalle!), "materiales", 0, "007e3"), "1e1");
    expect(cuerpoDeApu(4, base)).toEqual({
      rev: 4,
      rendimiento: "1e1",
      materiales: ["007e3"],
      equipos: ["1"],
      mano_obra: ["1", "1"],
    });
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

  test("un texto que no trae el prefijo queda igual", () => {
    expect(textoDeEstado("ERROR: algo")).toBe("ERROR: algo");
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
