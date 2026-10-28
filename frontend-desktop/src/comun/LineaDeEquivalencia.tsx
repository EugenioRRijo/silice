import { centesimasEsVe, fechaEsVe, formatoEsVe } from "../indicadores/formatoEsVe";

// La equivalencia de un precio del corte que se convirtio de otra moneda con la tasa del BCV (Tarea D2): precio
// original, tasa con su fecha y resultado, en una linea que quien revise despues pueda reconstruir. Lo que llega de la
// API es texto exacto con punto decimal; aqui solo se formatea (coma decimal, punto de miles), nunca se calcula: la
// operacion («×» o «÷») tambien la trae la API.
export interface Equivalencia {
  precio_original: string;
  moneda_original: string;
  tasa: string;
  fecha_tasa: string;
  fuente_tasa: string;
  // «BCV, publicacion del dd/mm/aaaa»: lo que se muestra; `fuente_tasa` es la referencia interna del rastro.
  fuente_legible: string;
  convertido: string;
  moneda: string;
  operacion: string;
}

// «31,50 USD × 36,50 Bs/USD (BCV del 20/10/2026) = 1.149,75 Bs». El resultado se lee en centesimas; el exacto va en el
// `title` de `LineaDeEquivalencia`.
export function textoDeEquivalencia(e: Equivalencia): string {
  return (
    `${formatoEsVe(e.precio_original)} ${e.moneda_original} ${e.operacion} ${formatoEsVe(e.tasa)} Bs/USD ` +
    `(BCV del ${fechaEsVe(e.fecha_tasa)}) = ${centesimasEsVe(e.convertido)} ${e.moneda}`
  );
}

// Para las lineas de estado, que son texto: la linea y el resultado exacto aparte (la centesima redondea).
export function textoDeEquivalenciaExacta(e: Equivalencia): string {
  return `${textoDeEquivalencia(e)}. Resultado exacto: ${formatoEsVe(e.convertido)} ${e.moneda}.`;
}

export function LineaDeEquivalencia({ equivalencia }: { equivalencia: Equivalencia }) {
  const exacto = `Resultado exacto: ${formatoEsVe(equivalencia.convertido)} ${equivalencia.moneda}. Fuente de la tasa: ${equivalencia.fuente_legible}.`;
  return (
    <span className="silice-cifra" title={exacto}>
      {textoDeEquivalencia(equivalencia)}
    </span>
  );
}
