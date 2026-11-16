// Lógica pura de «Un índice en USD» (RF-214, ola 2, línea 4, 2026-11-13). La API expresa en USD un índice mensual en
// bolívares (cada mes ÷ el promedio de la tasa del BCV de cada día del mes) y trae ya escritas en es-VE las cifras de la
// muestra; aquí solo se arman los textos y las filas de las tablas. La interfaz no calcula nada.
import type { ColumnaDensa, FilaDensa } from "../../comun/TablaDensa";

export const AYUDA_USD =
  "Para el reajuste de un contrato en dólares, un índice en bolívares cuenta dos veces la devaluación. Aquí se expresa " +
  "en USD: el valor de cada mes se divide entre el promedio de la tasa del BCV de los días de ese mes, y la serie nueva " +
  "se guarda para citarla en la cláusula del reajuste. «Revisar» no escribe nada.";
export const SIN_ORIGENES =
  "No hay índices mensuales en bolívares importados: importe el INPC (o una serie en CSV con la unidad indice_bs) arriba.";
export const YA_GUARDADA = "Ya está guardada con estos mismos valores.";
export const SIN_MESES = "Ningún mes se puede expresar en USD con las tasas importadas.";

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

export const COLUMNAS_MUESTRA: ColumnaDensa[] = [
  { clave: "mes", titulo: "Mes", ordenable: false },
  { clave: "indice_bs", titulo: "Índice en Bs", numerica: true, ordenable: false },
  { clave: "tasa_promedio", titulo: "Tasa promedio del mes (Bs/USD)", numerica: true, ordenable: false },
  { clave: "valor", titulo: "Índice en USD", numerica: true, ordenable: false },
];
export const COLUMNAS_OMITIDOS: ColumnaDensa[] = [
  { clave: "mes", titulo: "Mes", ordenable: false },
  { clave: "motivo", titulo: "Por qué no", ordenable: false },
];

export function filasMuestra(muestra: MesDeMuestra[]): FilaDensa[] {
  return muestra.map((m, i) => ({ id: `${i}-${m.mes}`, ...m }));
}

export function filasOmitidos(omitidos: MesSinUsd[]): FilaDensa[] {
  return omitidos.map((o, i) => ({ id: `${i}-${o.mes}`, ...o }));
}

// «2 meses en USD, de 01/2026 a 02/2027 (1 provisional).»; sin meses, el aviso de que no hay ninguno.
export function textoDelResumen(vista: VistaEnUsd): string {
  if (vista.meses === 0) return SIN_MESES;
  const meses = vista.meses === 1 ? "1 mes" : `${vista.meses} meses`;
  const provisionales =
    vista.provisionales === 0
      ? ""
      : ` (${vista.provisionales} ${vista.provisionales === 1 ? "provisional" : "provisionales"})`;
  return `${meses} en USD, de ${vista.desde} a ${vista.hasta}${provisionales}.`;
}
