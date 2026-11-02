// Lectura de referencias A1 de Excel (base 1, letras) a posiciones de lienzo (base 0). `aBase0` es la UNICA
// resta de uno del frontend: aUniver.ts, visor/celdas.ts y este modulo la usan, nadie mas.
export const MAX_FILAS_EXCEL = 1_048_576;
export const MAX_COLUMNAS_EXCEL = 16_384; // XFD

// Fila o columna de Excel (base 1) a posicion de Univer (base 0).
export function aBase0(n: number): number {
  return n - 1;
}

// Fila de Excel (base 1) desde una posicion de Univer (base 0): para decir "fila 19" como la ve el auditor.
export function aFilaExcel(fila0: number): number {
  return fila0 + 1;
}

// 0 -> "A", 25 -> "Z", 26 -> "AA", 16383 -> "XFD".
export function columna0ALetras(columna0: number): string {
  let n = aFilaExcel(columna0);
  let letras = "";
  while (n > 0) {
    const resto = (n - 1) % 26;
    letras = String.fromCharCode(65 + resto) + letras;
    n = Math.floor((n - 1) / 26);
  }
  return letras;
}

export interface Posicion0 {
  fila0: number;
  columna0: number;
}

const A1 = /^\$?([A-Za-z]{1,3})\$?([0-9]{1,7})$/;

// "A" -> 0, "Z" -> 25, "AA" -> 26, "XFD" -> 16383.
export function letrasAColumna0(letras: string): number {
  let n = 0;
  for (const c of letras.toUpperCase()) n = n * 26 + (c.charCodeAt(0) - 64);
  return aBase0(n);
}

// "F12" -> { fila0: 11, columna0: 5 }; null si no es una celda A1 dentro de los limites de Excel.
export function parsearA1(ref: string): Posicion0 | null {
  const m = A1.exec(ref);
  if (!m) return null;
  const columna0 = letrasAColumna0(m[1]);
  const fila = Number(m[2]);
  if (columna0 < 0 || columna0 >= MAX_COLUMNAS_EXCEL) return null;
  if (fila < 1 || fila > MAX_FILAS_EXCEL) return null;
  return { fila0: aBase0(fila), columna0 };
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
