import { describe, expect, test } from "vitest";
import { planDeDesplazamiento, rectanguloEnPantalla } from "./geometria";
import type { EntradaRectangulo } from "./geometria";

// Celda C5 (fila0 4, columna0 2) de una hoja con cabecera de 46 x 20 px y celdas de 64 x 20 px:
// en coordenadas de la hoja (cabecera incluida) empieza en x = 46 + 2*64 = 174 e y = 20 + 4*20 = 100.
function entrada(extra: Partial<EntradaRectangulo> = {}): EntradaRectangulo {
  return {
    celda: { fila0: 4, columna0: 2, startX: 174, endX: 238, startY: 100, endY: 120 },
    scroll: { x: 0, y: 0 },
    principal: { left: 46, top: 20 },
    congelado: { xSplit: 0, ySplit: 0, startRow: 0, startColumn: 0, ancho: 0, alto: 0 },
    cabecera: { ancho: 46, alto: 20 },
    escala: { x: 1, y: 1 },
    ...extra,
  };
}

describe("rectanguloEnPantalla", () => {
  test("sin panel fijo ni desplazamiento, la celda esta donde dice la hoja", () => {
    expect(rectanguloEnPantalla(entrada())).toEqual({ izquierda: 174, arriba: 100, derecha: 238, abajo: 120 });
  });

  test("al desplazar, la celda se corre lo mismo", () => {
    const r = rectanguloEnPantalla(entrada({ scroll: { x: 64, y: 40 } }));
    expect(r).toEqual({ izquierda: 110, arriba: 60, derecha: 174, abajo: 80 });
  });

  test("con una fila y una columna fijas, lo fijo no se desplaza y lo demas se recorta bajo el borde", () => {
    // Fijas: columna A (64 px) y fila 1 (20 px): el borde fijo esta en x = 46 + 64 = 110 e y = 20 + 20 = 40.
    const congelado = { xSplit: 1, ySplit: 1, startRow: 1, startColumn: 1, ancho: 64, alto: 20 };
    const principal = { left: 110, top: 40 };
    // La celda fija A1 (x 46..110, y 20..40) no se mueve aunque se desplace la hoja.
    const fija = entrada({
      celda: { fila0: 0, columna0: 0, startX: 46, endX: 110, startY: 20, endY: 40 },
      scroll: { x: 200, y: 200 },
      principal,
      congelado,
    });
    expect(rectanguloEnPantalla(fija)).toEqual({ izquierda: 46, arriba: 20, derecha: 110, abajo: 40 });
    // La celda C5 desplazada 100 px a la izquierda quedaria en x 74..138: lo que pasa del borde fijo (110) se recorta.
    const movil = entrada({ scroll: { x: 100, y: 0 }, principal, congelado });
    expect(rectanguloEnPantalla(movil)).toEqual({ izquierda: 110, arriba: 100, derecha: 138, abajo: 120 });
  });

  test("una celda que se desplazo por completo bajo el panel fijo no tiene rectangulo", () => {
    const congelado = { xSplit: 1, ySplit: 0, startRow: 0, startColumn: 1, ancho: 64, alto: 0 };
    const r = rectanguloEnPantalla(entrada({ scroll: { x: 200, y: 0 }, principal: { left: 110, top: 20 }, congelado }));
    expect(r).toBeNull();
  });

  test("con zoom 1,25 todo se agranda lo mismo", () => {
    const r = rectanguloEnPantalla(entrada({ escala: { x: 1.25, y: 1.25 } }));
    expect(r).toEqual({ izquierda: 217.5, arriba: 125, derecha: 297.5, abajo: 150 });
  });

  test("una fila o columna oculta (ancho cero) no tiene rectangulo", () => {
    const r = rectanguloEnPantalla(entrada({ celda: { fila0: 4, columna0: 2, startX: 174, endX: 174, startY: 100, endY: 120 } }));
    expect(r).toBeNull();
  });
});

describe("planDeDesplazamiento", () => {
  const base = {
    celda: { fila0: 30, columna0: 3 },
    ancho: () => 100,
    alto: () => 20,
    area: { ancho: 900, alto: 400 },
    congelado: { startRow: 0, startColumn: 0, ancho: 0, alto: 0 },
    primeraVisible: { fila0: 0, columna0: 0 },
    visible: { horizontal: true, vertical: false },
  };

  test("si la celda ya se ve entera no se desplaza", () => {
    expect(planDeDesplazamiento({ ...base, visible: { horizontal: true, vertical: true } })).toBeNull();
  });

  test("si ya se ve en horizontal, desplaza solo en vertical y deja unas filas de contexto arriba", () => {
    const plan = planDeDesplazamiento({ ...base, primeraVisible: { fila0: 0, columna0: 2 } });
    expect(plan).toEqual({ fila0: 27, columna0: 2 });
  });

  test("si no se ve en horizontal y cabe desde el principio, vuelve a la primera columna (descripcion visible)", () => {
    // Columnas 0..3 miden 400 px: caben en los 900 px del area.
    const plan = planDeDesplazamiento({ ...base, visible: { horizontal: false, vertical: true }, primeraVisible: { fila0: 0, columna0: 10 } });
    expect(plan).toEqual({ fila0: 0, columna0: 0 });
  });

  test("si no se ve en horizontal y no cabe desde el principio, queda a un tercio del ancho desde la izquierda", () => {
    // Columna 20: a la izquierda debe haber 300 px (un tercio de 900) = 3 columnas de 100 px.
    const plan = planDeDesplazamiento({
      ...base,
      celda: { fila0: 2, columna0: 20 },
      visible: { horizontal: false, vertical: true },
    });
    expect(plan).toEqual({ fila0: 0, columna0: 17 });
  });

  test("no baja de la primera fila ni de la primera columna fijas", () => {
    const plan = planDeDesplazamiento({
      ...base,
      celda: { fila0: 3, columna0: 1 },
      visible: { horizontal: false, vertical: false },
      congelado: { startRow: 2, startColumn: 1, ancho: 100, alto: 40 },
    });
    expect(plan?.fila0).toBeGreaterThanOrEqual(2);
    expect(plan?.columna0).toBeGreaterThanOrEqual(1);
  });

  test("una fila alta se ve entera: se quitan filas de contexto hasta que quepa", () => {
    // Fila de 350 px en un area de 400: con 3 filas de contexto (60 px) mas la fila son 410 > 400.
    const plan = planDeDesplazamiento({
      ...base,
      alto: (f) => (f === 30 ? 350 : 20),
      visible: { horizontal: true, vertical: false },
    });
    expect(plan?.fila0).toBe(28);
  });

  test("los paneles fijos le quitan alto a la zona donde debe caber la celda", () => {
    const filaAlta = { ...base, alto: (f: number) => (f === 30 ? 320 : 20), visible: { horizontal: true, vertical: false } };
    // Sin paneles fijos caben 3 filas de contexto: 60 + 320 = 380 <= 400.
    expect(planDeDesplazamiento(filaAlta)?.fila0).toBe(27);
    // Con 40 px de filas fijas quedan 360: hay que quitar una fila de contexto (360 <= 360).
    const conFijas = { ...filaAlta, congelado: { startRow: 2, startColumn: 0, ancho: 0, alto: 40 } };
    expect(planDeDesplazamiento(conFijas)?.fila0).toBe(28);
  });

  test("una fila mas alta que el area se deja arriba del todo", () => {
    const plan = planDeDesplazamiento({ ...base, alto: (f) => (f === 30 ? 500 : 20) });
    expect(plan?.fila0).toBe(30);
  });

  test("las columnas ocultas (ancho cero) no cuentan", () => {
    const plan = planDeDesplazamiento({
      ...base,
      celda: { fila0: 2, columna0: 9 },
      ancho: (c) => (c < 6 ? 0 : 200),
      visible: { horizontal: false, vertical: true },
    });
    // Desde la columna 0 hasta la 9 hay 4 columnas de 200 = 800 px <= 900: cabe desde el principio.
    expect(plan?.columna0).toBe(0);
  });
});

describe("planDeDesplazamiento: la descripcion de la fila no se pierde (M1)", () => {
  const base = {
    celda: { fila0: 4, columna0: 15 },
    ancho: () => 100,
    alto: () => 20,
    area: { ancho: 900, alto: 400 },
    congelado: { startRow: 0, startColumn: 0, ancho: 0, alto: 0 },
    primeraVisible: { fila0: 0, columna0: 0 },
    visible: { horizontal: false, vertical: true },
    descripcion: 3,
  };

  test("si la descripcion y la celda caben juntas, la descripcion queda visible con el menor desplazamiento", () => {
    // Columnas 3..15 miden 1300 px: no caben en 900. Con la celda en la 8 (columnas 3..8 = 600 px) si.
    const plan = planDeDesplazamiento({ ...base, celda: { fila0: 4, columna0: 8 } });
    // Desde la primera columna hasta la celda: 900 px (cabe): se vuelve a la primera.
    expect(plan?.columna0).toBe(0);
  });

  test("menor desplazamiento: la celda queda pegada al borde derecho y la descripcion se ve", () => {
    // Columnas 3..12 son 1000 px (no caben); con la celda en la 10: 3..10 = 800 px y desde 0..10 = 1100 (no cabe).
    const plan = planDeDesplazamiento({ ...base, celda: { fila0: 4, columna0: 10 }, primeraVisible: { fila0: 0, columna0: 0 } });
    // fmin: la primera columna tal que f..10 <= 900 px -> f = 2 (9 columnas); descripcion (3) >= 2: queda visible.
    expect(plan?.columna0).toBe(2);
  });

  test("ya en la celda pero con la descripcion fuera de la vista: tambien desplaza", () => {
    const plan = planDeDesplazamiento({
      ...base,
      celda: { fila0: 4, columna0: 10 },
      visible: { horizontal: true, vertical: true, descripcion: false },
      primeraVisible: { fila0: 0, columna0: 6 },
    });
    // Debe incluir la columna 3 y la 10: f..10 <= 900 -> f entre 2 y 3; el mas cercano a 6 es 3.
    expect(plan?.columna0).toBe(3);
  });

  test("si la descripcion y la celda no caben juntas, queda la celda (comportamiento anterior)", () => {
    const plan = planDeDesplazamiento({ ...base, celda: { fila0: 4, columna0: 20 } });
    expect(plan?.columna0).toBe(17);
  });

  test("con la celda y la descripcion ya a la vista no se desplaza", () => {
    const plan = planDeDesplazamiento({
      ...base,
      celda: { fila0: 4, columna0: 6 },
      visible: { horizontal: true, vertical: true, descripcion: true },
    });
    expect(plan).toBeNull();
  });

  test("sin descripcion se comporta como antes", () => {
    const plan = planDeDesplazamiento({ ...base, descripcion: undefined });
    expect(plan?.columna0).toBe(12);
  });
});
