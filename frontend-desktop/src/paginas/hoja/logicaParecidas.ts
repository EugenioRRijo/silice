// Logica pura de «Parecidas a esta descripción» (antes la pantalla «Partidas similares»; plan F4, Tarea 9): arma lo que se muestra con el texto que manda la API. No calcula ni
// redondea nada: los montos y puntajes llegan de la API con punto y solo se escriben en es-VE.
import type { FilaDensa } from "../../comun/TablaDensa";
import { formatoEsVe } from "../../indicadores/formatoEsVe";

export interface LineaMaterial {
  descripcion: string;
  unidad: string;
  cantidad: string;
  precio: string;
}
export interface LineaEquipo {
  descripcion: string;
  cantidad: string;
  precio: string;
  depreciacion: string;
}
export interface LineaManoObra {
  descripcion: string;
  cantidad: string;
  sueldo: string;
}
export interface Composicion {
  unidad: string;
  rendimiento: string;
  materiales: LineaMaterial[];
  equipos: LineaEquipo[];
  mano_obra: LineaManoObra[];
}
export interface Propuesta {
  codigo: string;
  descripcion: string;
  puntaje: string;
  puntaje_corto: string;
  composicion: Composicion | null;
  aviso: string | null;
}
// POST /v1/similares. `falla` (modelo o modulo no disponible) y `mensaje` (nada supera el umbral) son textos
// para la persona; con propuestas, ambos son null.
export interface SimilaresRespuesta {
  propuestas: Propuesta[];
  falla: string | null;
  mensaje: string | null;
}

export function descripcionLista(texto: string): boolean {
  return texto.trim() !== "";
}

// Las cifras llegan de la API con punto decimal y se formatean en es-VE una sola vez, aqui o en `presentar` de la
// tabla (decision de Eugenio, 2026-10-25: toda salida numerica en es-VE). Nada se calcula.
export function tituloDePropuesta(p: Propuesta): string {
  return `${formatoEsVe(p.puntaje_corto)} - ${p.codigo} - ${p.descripcion}`;
}

export function origenDePropuesta(p: Propuesta): string {
  return `Partida de origen: ${p.codigo} | puntaje de similitud: ${formatoEsVe(p.puntaje)}`;
}

export function encabezadoDeLista(cantidad: number): string {
  return cantidad === 1 ? "1 propuesta" : `${cantidad} propuestas, de mayor a menor similitud`;
}

export const ROTULO_MATERIALES = "Materiales";
export const ROTULO_EQUIPOS = "Equipos";
export const ROTULO_MANO_DE_OBRA = "Mano de obra";

export const AYUDA =
  "¿No la encuentra por su código? Escriba en «Partida» cómo se describe y pulse «Buscar parecidas»: Sílice propone las más parecidas del catálogo, con su análisis.";

// Unidad y rendimiento de la API; la interfaz solo escribe el rendimiento en es-VE y le agrega la unidad de tiempo.
export function rendimientoEnTexto(c: Composicion): { unidad: string; rendimiento: string } {
  return { unidad: c.unidad, rendimiento: `${formatoEsVe(c.rendimiento)} ${c.unidad}/día` };
}

export function resultadosDe(buscado: string): string {
  return `Resultados de: “${buscado.trim()}”`;
}

// Las filas llevan un id estable (la posicion) porque una descripcion puede repetirse.
export function filasMateriales(c: Composicion): FilaDensa[] {
  return c.materiales.map((l, i) => ({ id: String(i), ...l }));
}
export function filasEquipos(c: Composicion): FilaDensa[] {
  return c.equipos.map((l, i) => ({ id: String(i), ...l }));
}
export function filasManoObra(c: Composicion): FilaDensa[] {
  return c.mano_obra.map((l, i) => ({ id: String(i), ...l }));
}
