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
  if (sentido === "exactitud") return "desfavorable"; // el signo solo mueve la flecha
  const sube = haySubida(texto);
  if (sentido === "costo") return sube ? "desfavorable" : "favorable";
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
