// Una fecha que la persona escribe en un campo de texto (Lote G5, «Fecha de entrega al cliente»): se escribe como se
// lee en es-VE (dd/mm/aaaa) y viaja como la espera la API (aaaa-mm-dd). Para leer una fecha de la API está `fechaEsVe`
// (`indicadores/formatoEsVe.ts`). Va en texto y no en el calendario de Carbon: flatpickr corre en silencio un día que
// no existe al mes siguiente («31/02/2026» quedaba en «03/03/2026»); aquí se rechaza con lo que escribió la persona.

export const MENSAJE_FORMA_DE_FECHA = "Escriba la fecha como dd/mm/aaaa.";
export const MENSAJE_FECHA_INEXISTENTE = "La fecha escrita no existe en el calendario.";

const ES_VE = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/;
const DOS = (n: number) => String(n).padStart(2, "0");

// Vacía es «sin fecha» (`iso: null`); si no, la fecha real en aaaa-mm-dd o el mensaje para la persona.
export function leerFechaEscrita(texto: string): { ok: true; iso: string | null } | { ok: false; error: string } {
  const limpio = texto.trim();
  if (limpio === "") return { ok: true, iso: null };
  const m = ES_VE.exec(limpio);
  if (!m) return { ok: false, error: MENSAJE_FORMA_DE_FECHA };
  const [dia, mes, anio] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const fecha = new Date(Date.UTC(anio, mes - 1, dia));
  if (fecha.getUTCFullYear() !== anio || fecha.getUTCMonth() !== mes - 1 || fecha.getUTCDate() !== dia) {
    return { ok: false, error: MENSAJE_FECHA_INEXISTENTE };
  }
  return { ok: true, iso: `${anio}-${DOS(mes)}-${DOS(dia)}` };
}

// El día de hoy en la hora local del equipo, como aaaa-mm-dd (Sílice corre en el mismo equipo que su servidor).
export function hoyIso(ahora: Date = new Date()): string {
  return `${ahora.getFullYear()}-${DOS(ahora.getMonth() + 1)}-${DOS(ahora.getDate())}`;
}

// Si `iso` es un día anterior a `hoy` (las dos en aaaa-mm-dd, que se ordenan como texto).
export function anteriorA(iso: string, hoy: string): boolean {
  return iso < hoy;
}
