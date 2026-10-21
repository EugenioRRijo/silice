import type { SentidoIndicador } from "./tipos";

export type SemanticaIbcs = "favorable" | "desfavorable" | "neutro";

// Cero escrito como texto decimal: "0", "0.00", "-0.00", ".0". Sin Number(): el signo se lee del texto y un
// monto con muchos decimales no pierde precision. Se admite tambien un "+" explicito.
const CERO = /^[-+]?0*(\.0*)?$/;

// IBCS: el color expresa el impacto sobre el presupuesto, no el signo. En un costo subir es desfavorable;
// en un rendimiento subir es favorable.
export function semanticaIbcs(delta: string, sentido: SentidoIndicador): SemanticaIbcs {
  const texto = delta.trim();
  if (CERO.test(texto)) return "neutro";
  const sube = haySubida(texto);
  // «exactitud» (el libro contra Silice): decision de Eugenio (V-16), el libro menor es favorable (verde) y el mayor,
  // desfavorable (rojo); como en un costo, el signo decide el color y la flecha dice el sentido.
  if (sentido === "costo" || sentido === "exactitud") return sube ? "desfavorable" : "favorable";
  return sube ? "favorable" : "desfavorable";
}

export function haySubida(delta: string): boolean {
  return !delta.trim().startsWith("-");
}

export const TEXTO_SEMANTICA: Record<SemanticaIbcs, string> = {
  favorable: "favorable",
  desfavorable: "desfavorable",
  neutro: "sin variación",
};
