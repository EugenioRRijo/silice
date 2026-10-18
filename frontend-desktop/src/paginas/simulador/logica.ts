// Logica pura del simulador de listas. La interfaz no simula ni calcula precios: arma el cuerpo, valida lo que la
// pantalla de Streamlit validaba al escribir (la semilla) y deja que la API valide el resto con sus mensajes.
import type { FilaDensa } from "../../comun/TablaDensa";

export const SEMILLA_INICIAL = "42";
export const VARIACION_INICIAL = "5";
export const MENSAJE_SIN_FILAS = "La simulacion no produjo ninguna fila (revise el filtro de insumos).";
export const MENSAJE_SEMILLA = "La semilla debe ser un número entero mayor o igual a 0.";
export const AVISO_HERRAMIENTA =
  "Toma la lista de precios vigente del catálogo y aplica variaciones deterministas según una semilla, en el " +
  "formato tipo,insumo,unidad,precio. Herramienta de prueba, no una fuente de mercado.";

// Mismo tope que la API (aplicacion/simulador.py: VARIACION_MAXIMA). La coma decimal no se acepta: la API tampoco.
export const TOPE_VARIACION = 1000;
export const MENSAJE_VARIACION = `La variación máxima debe ser un número decimal, con punto, entre 0 y ${TOPE_VARIACION}.`;
const DECIMAL_DE_LA_API = /^\+?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/;

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

// Divergencia conocida: aqui la semilla llega hasta 2^53-1 (el mayor entero exacto de JS, que es lo que viaja en el
// JSON); la API admite hasta 2^63-1. Una semilla mayor solo se puede pedir por la API, no desde esta pantalla.
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

// null si la variacion sirve; si no, el texto junto al campo. Es la misma regla que la API (decimal finito, de 0 a
// 1000); comparar con el tope no es calcular un monto. Un exponente enorme da Infinity y se rechaza.
export function errorDeVariacion(texto: string): string | null {
  const limpio = texto.trim();
  if (!DECIMAL_DE_LA_API.test(limpio)) return MENSAJE_VARIACION;
  return Number(limpio) <= TOPE_VARIACION ? null : MENSAJE_VARIACION;
}

// Los valores con que se pidio el resultado que esta en pantalla.
export function resumenDeEnvio(cuerpo: CuerpoSimulacion): string {
  return `semilla ${cuerpo.semilla}, variación ${cuerpo.variacion_max} %, insumos: ${cuerpo.insumos ?? "todos"}`;
}
