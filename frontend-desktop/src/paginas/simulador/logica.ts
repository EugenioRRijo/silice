// Logica pura del simulador de listas. La interfaz no simula ni calcula precios: arma el cuerpo, valida lo que la
// pantalla de Streamlit validaba al escribir (la semilla) y deja que la API valide el resto con sus mensajes.
import type { FilaDensa } from "../../comun/TablaDensa";

export const SEMILLA_INICIAL = "42";
export const VARIACION_INICIAL = "5";
export const MENSAJE_SIN_FILAS = "La simulacion no produjo ninguna fila (revise el filtro de insumos).";
export const MENSAJE_SEMILLA = "La semilla debe ser un número entero mayor o igual a 0.";
export const AVISO_HERRAMIENTA =
  "Toma la lista de precios vigente del catálogo y aplica variaciones deterministas según una semilla, en el " +
  "formato tipo,insumo,unidad,precio. Herramienta de prueba, no una fuente de mercado (UC-07 es I6.3).";

export interface Formulario {
  semilla: string;
  variacion: string;
  insumos: string;
}

export interface CuerpoSimulacion {
  semilla: number;
  variacion_max: string;
  insumos: string | null;
}

export interface FilaSimulada {
  tipo: string;
  insumo: string;
  unidad: string;
  precio: string;
}

// null si la semilla sirve; si no, el texto que se muestra junto al campo (Streamlit no deja escribir negativos).
export function errorDeSemilla(texto: string): string | null {
  const limpio = texto.trim();
  if (!/^\d+$/.test(limpio) || !Number.isSafeInteger(Number(limpio))) return MENSAJE_SEMILLA;
  return null;
}

// El cuerpo de POST /v1/simulador: la variacion viaja como texto (la API la interpreta); insumos vacios = todos.
export function cuerpoDe(formulario: Formulario): CuerpoSimulacion {
  const insumos = formulario.insumos.trim();
  return {
    semilla: Number(formulario.semilla.trim()),
    variacion_max: formulario.variacion,
    insumos: insumos === "" ? null : insumos,
  };
}

export function filasDeTabla(filas: FilaSimulada[]): FilaDensa[] {
  return filas.map((f, i) => ({ id: String(i), tipo: f.tipo, insumo: f.insumo, unidad: f.unidad, precio: f.precio }));
}
