// Esqueleto para ver el rojo (RF-214).
export interface SerieDeOrigen {
  clave: string;
  nombre: string;
  organismo: string;
}
export interface OrigenesEnUsd {
  series: SerieDeOrigen[];
  lados: string[];
  lado_por_omision: string;
}
export interface MesDeMuestra {
  mes: string;
  indice_bs: string;
  tasa_promedio: string;
  valor: string;
}
export interface MesSinUsd {
  mes: string;
  motivo: string;
}
export interface VistaEnUsd {
  serie_nueva: string;
  nombre: string;
  meses: number;
  desde: string;
  hasta: string;
  provisionales: number;
  muestra: MesDeMuestra[];
  omitidos: MesSinUsd[];
  huella: string;
  ya_guardada: boolean;
}
export function textoDelResumen(vista: VistaEnUsd): string {
  throw new Error(`sin construir: ${vista.serie_nueva}`);
}
