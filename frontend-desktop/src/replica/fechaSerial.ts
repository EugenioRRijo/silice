// Fecha ISO del contrato ("2026-10-18" o "2026-10-18T12:00:00") al numero de serie de Excel, sistema 1900, para que
// Univer la muestre con el patron de fecha del libro (d-mmm-yy, dd/mm/yyyy, mmmm...). Es aritmetica de calendario
// sobre enteros, no dinero.
const ISO = /^([0-9]{4})-([0-9]{2})-([0-9]{2})(?:[T ]([0-9]{2}):([0-9]{2})(?::([0-9]{2}))?)?/;
const DIA_MS = 86_400_000;
// 1899-12-30 es el dia 0 de Excel para fechas desde el 1 de marzo de 1900; antes de esa fecha Excel cuenta un
// 29 de febrero de 1900 que no existio, y el dia 0 efectivo es el 31 de diciembre de 1899.
const CERO_1900 = Date.UTC(1899, 11, 30);
const PRIMERO_MARZO_1900 = Date.UTC(1900, 2, 1);

export function serialDeExcel(iso: string): number | null {
  const m = ISO.exec(iso);
  if (!m) return null;
  const [, anio, mes, dia, hora = "0", minuto = "0", segundo = "0"] = m;
  const fecha = Date.UTC(Number(anio), Number(mes) - 1, Number(dia));
  if (Number.isNaN(fecha)) return null;
  const dias = Math.round((fecha - CERO_1900) / DIA_MS) - (fecha < PRIMERO_MARZO_1900 ? 1 : 0);
  const fraccion = (Number(hora) * 3600 + Number(minuto) * 60 + Number(segundo)) / 86_400;
  return dias + fraccion;
}
