// Fechas de Control (VB-19 y ronda 1 del árbitro). Una fecha se formatea solo en su ranura: un campo de la API que es
// una fecha ISO y nada más (el corte, el corte de una valuación registrada). Las frases que arma la API ya traen sus
// fechas en dd/mm/aaaa; el texto del usuario (un número de valuación, un código) nunca se reescribe.
import { fechaEsVe } from "../../indicadores/formatoEsVe";

const ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

// Si el día y el mes existen en ese año («2026-02-30» y «1234-56-78» no).
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

// Los feriados se escriben como se leen (25/12/2026; también se acepta 2026-12-25) separados por comas, punto y coma
// o saltos de línea, y viajan como los espera la API (2026-12-25, separados por comas). Uno que no es una fecha real
// se rechaza aquí, con lo que escribió la persona, para que el mensaje no muestre un valor que no escribió.
const FECHA_ES_VE = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;
const DOS = (n: number) => String(n).padStart(2, "0");

export function leerFeriados(texto: string): { feriados: string } | { error: string } {
  const leidos: string[] = [];
  for (const parte of texto.split(/[,;\n]/)) {
    const escrito = parte.trim();
    if (escrito === "") continue;
    const es = FECHA_ES_VE.exec(escrito);
    const iso = ISO.exec(escrito);
    const [anio, mes, dia] = es ? [es[3], es[2], es[1]].map(Number) : iso ? [iso[1], iso[2], iso[3]].map(Number) : [0, 0, 0];
    if ((!es && !iso) || !fechaReal(anio, mes, dia)) {
      return { error: `Escriba los feriados como dd/mm/aaaa, separados por comas: «${escrito}» no es una fecha.` };
    }
    leidos.push(`${anio}-${DOS(mes)}-${DOS(dia)}`);
  }
  return { feriados: leidos.join(", ") };
}
