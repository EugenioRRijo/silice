// Fechas de Control (VB-19 y ronda 1 del árbitro). Una fecha se formatea solo en su ranura: un campo de la API que es
// una fecha ISO y nada más (el corte, el corte de una valuación registrada). Las frases que arma la API ya traen sus
// fechas en dd/mm/aaaa; el texto del usuario (un número de valuación, un código) nunca se reescribe.
import { fechaEsVe } from "../../indicadores/formatoEsVe";

const ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

// La fecha del calendario, o null si el día o el mes no existen («2026-02-30», «1234-56-78»).
function fechaReal(anio: number, mes: number, dia: number): boolean {
  const d = new Date(Date.UTC(anio, mes - 1, dia));
  return d.getUTCFullYear() === anio && d.getUTCMonth() === mes - 1 && d.getUTCDate() === dia;
}

// «2026-11-13» -> «13/11/2026». Lo que no es exactamente una fecha ISO real se devuelve tal cual.
export function fechaDeRanura(texto: string): string {
  const m = ISO.exec(texto);
  if (!m || !fechaReal(Number(m[1]), Number(m[2]), Number(m[3]))) return texto;
  return fechaEsVe(texto);
}

// Los feriados se escriben como se leen (25/12/2026) y viajan como los espera la API (2026-12-25). Lo que no parece
// una fecha dd/mm/aaaa pasa tal cual: la API dice que esta mal.
const FECHA_ES_VE = /\b(\d{1,2})\/(\d{1,2})\/(\d{4})\b/g;

export function feriadosParaEnviar(texto: string): string {
  return texto.replace(FECHA_ES_VE, (_, dia: string, mes: string, anio: string) =>
    `${anio}-${mes.padStart(2, "0")}-${dia.padStart(2, "0")}`,
  );
}
