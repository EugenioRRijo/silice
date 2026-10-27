import type { Oferta } from "./oferta";
import type { ObraDeCarpeta } from "./useObras";

export interface Resultado {
  texto: string;
  detalle: string;
  ruta: string;
}

export const MAXIMO_DE_RESULTADOS = 8;

export function resultadosDe(_texto: string, _obras: readonly ObraDeCarpeta[], _oferta?: Oferta): Resultado[] {
  return [];
}
