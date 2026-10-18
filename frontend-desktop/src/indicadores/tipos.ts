// Contrato de la API para la franja de indicadores (RS2-7). Los montos llegan como texto decimal y la
// interfaz solo los muestra: nunca los recalcula.
export type SentidoIndicador = "costo" | "rendimiento";

export type Severidad = "CRITICO" | "ERROR" | "ADVERTENCIA" | "INFO";

export interface IndicadorRespuesta {
  clave: string;
  titulo: string;
  actual: string;
  meta: string;
  delta: string;
  delta_pct: string | null;
  sentido: SentidoIndicador;
}

export type ConteoPorSeveridad = Record<Severidad, number>;
