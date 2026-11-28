// La lógica pura de la actividad de una cuenta (`GET /v1/actividad`): niveles del calendario por cuantiles, semanas,
// rótulos de meses y textos del día. Sin React ni red: se prueba sola (logica.test.ts).
import { fechaEsVe } from "../../indicadores/formatoEsVe";

export type TipoDeEvento = "version_guardada" | "version_enviada" | "dictamen" | "auditoria";

export interface DiaDeActividad {
  // AAAA-MM-DD
  fecha: string;
  cuantos: number;
}

export interface CifrasDeActividad {
  versiones_guardadas: number;
  versiones_enviadas: number;
  dictamenes: number;
  auditorias: number;
}

export interface EventoDeActividad {
  // ISO con hora, sin zona: AAAA-MM-DDTHH:MM:SS
  fecha: string;
  tipo: TipoDeEvento;
  obra: string;
  archivo: string;
  texto: string;
}

export interface ActividadRespuesta {
  usuario: string;
  desde: string;
  hasta: string;
  dias: DiaDeActividad[];
  cifras: CifrasDeActividad;
  eventos: EventoDeActividad[];
  recortado: boolean;
}

// 0 = sin actividad; 1 a 4 = de menos a más, una sola tinta (--silice-serie-1) cada vez más intensa.
export type Nivel = 0 | 1 | 2 | 3 | 4;
export const NIVELES: readonly Nivel[] = [0, 1, 2, 3, 4];

// Cuantil por rango más cercano (nearest-rank) de una lista ya ordenada de menor a mayor.
function cuantil(ordenados: readonly number[], p: number): number {
  const posicion = Math.max(1, Math.ceil(p * ordenados.length));
  return ordenados[posicion - 1] ?? 0;
}

// Una función `cuantos -> nivel`. Los días sin actividad son el nivel 0; los demás se reparten en 4 niveles por los
// cuartiles de los días con actividad (un día con más acciones que el cuartil k sube de nivel). Si todos los días con
// actividad valen lo mismo, todos quedan en el nivel 1: la leyenda dice «Menos … Más», no una cantidad.
export function nivelesPorCuantiles(dias: readonly DiaDeActividad[]): (cuantos: number) => Nivel {
  const ordenados = dias
    .map((d) => d.cuantos)
    .filter((n) => n > 0)
    .sort((a, b) => a - b);
  const cortes = [cuantil(ordenados, 0.25), cuantil(ordenados, 0.5), cuantil(ordenados, 0.75)];
  return (cuantos) => {
    if (cuantos <= 0) return 0;
    return (1 + cortes.filter((corte) => cuantos > corte).length) as Nivel;
  };
}

// --- fechas ------------------------------------------------------------------------------------------------------------
// Las fechas viajan como AAAA-MM-DD y se calculan en UTC: sin horario de verano que corra un día.

const ISO = /^(\d{4})-(\d{2})-(\d{2})/;
const DIA_MS = 86_400_000;

function aUtc(fecha: string): number {
  const m = ISO.exec(fecha);
  if (!m) throw new Error(`Fecha inválida: ${fecha}`);
  return Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
}

function deUtc(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10);
}

export function sumarDias(fecha: string, dias: number): string {
  return deUtc(aUtc(fecha) + dias * DIA_MS);
}

// Lunes = 0 … domingo = 6.
function diaDeLaSemana(fecha: string): number {
  return (new Date(aUtc(fecha)).getUTCDay() + 6) % 7;
}

// dd/mm/aaaa (y, con hora, dd/mm/aaaa hh:mm).
export function fechaVe(iso: string): string {
  return fechaEsVe(iso);
}

export const DIAS_DE_LA_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"] as const;
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"] as const;

// Una semana del calendario: siete lugares, de lunes a domingo; `null` es un lugar fuera del período.
export type Semana = readonly (string | null)[];

// Las semanas (columnas) que cubren de `desde` a `hasta`, ambos incluidos, de la más antigua a la más nueva.
export function semanas(desde: string, hasta: string): Semana[] {
  if (aUtc(desde) > aUtc(hasta)) return [];
  const resultado: Semana[] = [];
  let lunes = sumarDias(desde, -diaDeLaSemana(desde));
  while (aUtc(lunes) <= aUtc(hasta)) {
    const semana: (string | null)[] = [];
    for (let i = 0; i < 7; i++) {
      const dia = sumarDias(lunes, i);
      semana.push(aUtc(dia) >= aUtc(desde) && aUtc(dia) <= aUtc(hasta) ? dia : null);
    }
    resultado.push(semana);
    lunes = sumarDias(lunes, 7);
  }
  return resultado;
}

export interface RotuloDeMes {
  // Índice de la semana (columna) donde empieza el rótulo.
  semana: number;
  mes: string;
}

// Un rótulo de tres letras ocupa unas tres columnas del calendario: más cerca que eso, dos rótulos se pisan, y menos de
// eso hasta el final, el último se sale de la caja.
export const COLUMNAS_POR_ROTULO = 3;

// El rótulo de cada mes, sobre la primera semana que lo trae. Si el mes siguiente empieza a menos de tres columnas, el mes
// que apenas asomaba (el primero del período, casi siempre) cede su rótulo; y un mes al que le quedan menos de tres
// columnas hasta el final no lleva rótulo.
export function rotulosDeMeses(columnas: readonly Semana[]): RotuloDeMes[] {
  const rotulos: RotuloDeMes[] = [];
  let anterior = -1;
  columnas.forEach((semana, i) => {
    const primero = semana.find((d): d is string => d !== null);
    if (primero === undefined) return;
    const mes = Number(primero.slice(5, 7)) - 1;
    if (mes === anterior) return;
    anterior = mes;
    if (columnas.length - i < COLUMNAS_POR_ROTULO && rotulos.length > 0) return;
    const previo = rotulos[rotulos.length - 1];
    if (previo !== undefined && i - previo.semana < COLUMNAS_POR_ROTULO) rotulos.pop();
    rotulos.push({ semana: i, mes: MESES[mes] ?? "" });
  });
  return rotulos;
}

// --- textos ------------------------------------------------------------------------------------------------------------

export function accionesEnTexto(cuantos: number): string {
  if (cuantos === 0) return "sin actividad";
  return cuantos === 1 ? "1 acción" : `${cuantos} acciones`;
}

// El nombre accesible de una celda: «19/10/2026: 2 acciones».
export function nombreDeCelda(fecha: string, cuantos: number): string {
  return `${fechaVe(fecha)}: ${accionesEnTexto(cuantos)}`;
}

export const TIPOS: readonly { tipo: TipoDeEvento; etiqueta: string }[] = [
  { tipo: "version_guardada", etiqueta: "Versiones guardadas" },
  { tipo: "version_enviada", etiqueta: "Versiones enviadas" },
  { tipo: "dictamen", etiqueta: "Dictámenes" },
  { tipo: "auditoria", etiqueta: "Auditorías" },
];

export function etiquetaDeTipo(tipo: TipoDeEvento): string {
  return TIPOS.find((t) => t.tipo === tipo)?.etiqueta ?? tipo;
}

// Las cifras del período, en el orden de TIPOS.
export function cifrasEnLista(cifras: CifrasDeActividad): { tipo: TipoDeEvento; etiqueta: string; cuantos: number }[] {
  const por: Record<TipoDeEvento, number> = {
    version_guardada: cifras.versiones_guardadas,
    version_enviada: cifras.versiones_enviadas,
    dictamen: cifras.dictamenes,
    auditoria: cifras.auditorias,
  };
  return TIPOS.map((t) => ({ ...t, cuantos: por[t.tipo] }));
}

// Los eventos de un tipo (null: todos), en el mismo orden en que llegan (lo más reciente primero).
export function filtrarEventos(eventos: readonly EventoDeActividad[], tipo: TipoDeEvento | null): EventoDeActividad[] {
  return tipo === null ? [...eventos] : eventos.filter((e) => e.tipo === tipo);
}

// Los eventos de un día (AAAA-MM-DD).
export function eventosDelDia(eventos: readonly EventoDeActividad[], fecha: string): EventoDeActividad[] {
  return eventos.filter((e) => e.fecha.slice(0, 10) === fecha);
}

// «guardó la versión VIV-001 de Vivienda» → «Guardó la versión VIV-001 de Vivienda».
export function conMayuscula(texto: string): string {
  return texto.charAt(0).toLocaleUpperCase("es") + texto.slice(1);
}

// De un día a otro, sin salirse de [desde, hasta]: para moverse con las flechas por el calendario.
export function moverFoco(actual: string, tecla: string, desde: string, hasta: string): string {
  const paso: Record<string, number> = { ArrowLeft: -7, ArrowRight: 7, ArrowUp: -1, ArrowDown: 1 };
  const delta = paso[tecla];
  if (delta === undefined) return actual;
  const destino = sumarDias(actual, delta);
  if (aUtc(destino) < aUtc(desde)) return desde;
  if (aUtc(destino) > aUtc(hasta)) return hasta;
  return destino;
}
