// Lectura de referencias A1 de Excel (base 1, letras) a posiciones de lienzo (base 0). Es la unica rutina del
// frontend que hace la resta de uno: aUniver.ts y visor/celdas.ts la usan, nadie mas.
export const MAX_FILAS_EXCEL = 1_048_576;
export const MAX_COLUMNAS_EXCEL = 16_384; // XFD

export interface Posicion0 {
  fila0: number;
  columna0: number;
}

const A1 = /^\$?([A-Za-z]{1,3})\$?([0-9]{1,7})$/;

// "A" -> 0, "Z" -> 25, "AA" -> 26, "XFD" -> 16383.
export function letrasAColumna0(letras: string): number {
  let n = 0;
  for (const c of letras.toUpperCase()) n = n * 26 + (c.charCodeAt(0) - 64);
  return n - 1;
}

// "F12" -> { fila0: 11, columna0: 5 }; null si no es una celda A1 dentro de los limites de Excel.
export function parsearA1(ref: string): Posicion0 | null {
  const m = A1.exec(ref);
  if (!m) return null;
  const columna0 = letrasAColumna0(m[1]);
  const fila = Number(m[2]);
  if (columna0 < 0 || columna0 >= MAX_COLUMNAS_EXCEL) return null;
  if (fila < 1 || fila > MAX_FILAS_EXCEL) return null;
  return { fila0: fila - 1, columna0 };
}

// "A1:D1" -> {startRow:0,startColumn:0,endRow:0,endColumn:3}; null si no es un rango A1.
export function parsearRango(rango: string): {
  startRow: number;
  startColumn: number;
  endRow: number;
  endColumn: number;
} | null {
  const partes = rango.split(":");
  if (partes.length !== 2) return null;
  const a = parsearA1(partes[0]);
  const b = parsearA1(partes[1]);
  if (!a || !b) return null;
  return { startRow: a.fila0, startColumn: a.columna0, endRow: b.fila0, endColumn: b.columna0 };
}
