// Logica pura de «Partidas similares»: arma lo que se muestra con el texto que manda la API. No calcula ni
// redondea nada (los montos y puntajes ya llegan formateados, como los de la pagina de Streamlit).
import type { FilaDensa } from "../../comun/TablaDensa";

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

export const AVISO_SIN_DESCRIPCION = "Escriba una descripción para buscar partidas similares.";

export function descripcionLista(texto: string): boolean {
  return texto.trim() !== "";
}

export function tituloDePropuesta(p: Propuesta): string {
  return `${p.puntaje_corto} - ${p.codigo} - ${p.descripcion}`;
}

export function origenDePropuesta(p: Propuesta): string {
  return `Partida de origen: ${p.codigo} | puntaje de similitud: ${p.puntaje}`;
}

export function encabezadoDeLista(cantidad: number): string {
  return `${cantidad} propuesta(s), de mayor a menor similitud`;
}

export function rendimientoEnTexto(c: Composicion): string {
  return `Unidad: ${c.unidad} | Rendimiento: ${c.rendimiento} ${c.unidad}/día`;
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
