// Fuente unica de la severidad: el color (token), el icono y el texto. La hoja, la lista y la franja la usan;
// el color nunca va solo.
import type { Severidad } from "../indicadores/tipos";

export type NombreDeIcono = "ErrorFilled" | "WarningFilled" | "WarningAltFilled" | "InformationFilled";

export interface EstiloDeSeveridad {
  token: string;
  icono: NombreDeIcono;
  texto: string;
}

// De mas a menos grave.
export const SEVERIDADES: readonly Severidad[] = ["CRITICO", "ERROR", "ADVERTENCIA", "INFO"];

const ESTILOS: Record<Severidad, EstiloDeSeveridad> = {
  CRITICO: { token: "--silice-sev-critico", icono: "ErrorFilled", texto: "Crítico" },
  ERROR: { token: "--silice-sev-error", icono: "WarningFilled", texto: "Error" },
  ADVERTENCIA: { token: "--silice-sev-advertencia", icono: "WarningAltFilled", texto: "Advertencia" },
  INFO: { token: "--silice-sev-info", icono: "InformationFilled", texto: "Información" },
};

export function normalizarSeveridad(texto: string): Severidad {
  return (SEVERIDADES as readonly string[]).includes(texto) ? (texto as Severidad) : "INFO";
}

export function estiloDeSeveridad(severidad: Severidad): EstiloDeSeveridad {
  return ESTILOS[severidad];
}

// Mas grande = mas grave.
export function gravedad(severidad: Severidad): number {
  return SEVERIDADES.length - 1 - SEVERIDADES.indexOf(severidad);
}
