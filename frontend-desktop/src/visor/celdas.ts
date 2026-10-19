import type { HojaVisualRespuesta } from "../api/tipos";
import { aFilaExcel, parsearA1 } from "../replica/coordenadas";
import { tipoDeValor } from "../replica/tipoDeValor";
import type { CeldaRef } from "./hojaVisor";

// "HOJA!REF" (sin comillas ni $) -> { hoja, fila0, columna0 } en base 0. Separa por el ULTIMO "!" porque el
// nombre de una hoja puede tener signos de cierre de exclamacion. null si la referencia no es una celda A1
// ("APU-01!Rendimiento"), si falta la hoja o si viene vacia: esos hallazgos no se pueden marcar en la hoja.
export function parsearCelda(celda: string): CeldaRef | null {
  const corte = celda.lastIndexOf("!");
  if (corte <= 0) return null;
  const hoja = celda.slice(0, corte);
  const posicion = parsearA1(celda.slice(corte + 1));
  if (!posicion) return null;
  return { hoja, ...posicion };
}

// La columna que dice de que trata la fila de un hallazgo: la del texto mas largo a la izquierda de la celda (sin
// contar numeros, fechas ni columnas ocultas). En una partida es la descripcion; null si no hay texto.
export function columnaDeDescripcion(hoja: HojaVisualRespuesta, fila0: number, columnaDeLaCelda0: number): number | null {
  let mejor: number | null = null;
  let largo = 0;
  for (const c of hoja.celdas) {
    const pos = parsearA1(c.ref);
    if (!pos || pos.fila0 !== fila0 || pos.columna0 >= columnaDeLaCelda0) continue;
    if (hoja.ocultas_columnas.includes(aFilaExcel(pos.columna0))) continue;
    if (tipoDeValor(c.mostrado) !== "texto") continue;
    const texto = c.mostrado.trim();
    if (texto.length > largo || (texto.length === largo && mejor !== null && pos.columna0 < mejor)) {
      mejor = pos.columna0;
      largo = texto.length;
    }
  }
  return mejor;
}
