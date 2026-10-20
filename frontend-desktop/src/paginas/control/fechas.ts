// VB-19: las fechas ISO que la API manda dentro de un texto («2026-11-02 a 2026-11-06», «día 12 (2026-11-18)») se
// leen en dd/mm/aaaa. Solo para mostrar: lo que se envia a la API sigue siendo AAAA-MM-DD. Cada fecha pasa por
// `fechaEsVe` (formatoEsVe.ts); una hora «HH:MM» pegada a la fecha se conserva. Lo que no es una fecha no se toca.
import { fechaEsVe } from "../../indicadores/formatoEsVe";

const FECHA_EN_TEXTO = /(?<![\d-])(\d{4}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2})(?::\d{2})?)?(?![\d-])/g;

export function fechasEsVe(texto: string): string {
  return texto.replace(FECHA_EN_TEXTO, (_, fecha: string, hora?: string) =>
    hora ? `${fechaEsVe(fecha)} ${hora}` : fechaEsVe(fecha),
  );
}

// Los feriados se escriben como se leen (25/12/2026) y viajan como los espera la API (2026-12-25). Lo que no parece
// una fecha dd/mm/aaaa pasa tal cual: la API dice que esta mal.
const FECHA_ES_VE = /\b(\d{1,2})\/(\d{1,2})\/(\d{4})\b/g;

export function feriadosParaEnviar(texto: string): string {
  return texto.replace(FECHA_ES_VE, (_, dia: string, mes: string, anio: string) =>
    `${anio}-${mes.padStart(2, "0")}-${dia.padStart(2, "0")}`,
  );
}
