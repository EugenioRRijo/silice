// Contrato de la API para la franja de indicadores (RS2-7). Los montos llegan como texto decimal y la
// interfaz solo los muestra: nunca los recalcula.
// "exactitud" (RS2-13): la meta es el valor correcto (el total de Silice). Decision de Eugenio (V-16): el libro menor
// que Silice es favorable (verde) y el mayor, desfavorable (rojo); el texto y la flecha acompanan al color.
export type SentidoIndicador = "costo" | "rendimiento" | "exactitud";

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
