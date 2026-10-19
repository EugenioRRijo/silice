import { ArrowDown, ArrowUp, Subtract } from "@carbon/icons-react";
import { haySubida, semanticaIbcs, TEXTO_SEMANTICA } from "../indicadores/ibcs";

// Una cifra de variacion de COSTO con la semantica IBCS (DESIGN.md): subir un costo es desfavorable, bajarlo es
// favorable, cero es neutro. El color nunca va solo: lleva una flecha y el texto accesible de la semantica. El texto
// del monto es el de la API, sin convertir a numero.
export function Variacion({ valor }: { valor: string }) {
  const semantica = semanticaIbcs(valor, "costo");
  const Icono = semantica === "neutro" ? Subtract : haySubida(valor) ? ArrowUp : ArrowDown;
  return (
    <span className={`silice-variacion ibcs-${semantica}`}>
      <Icono size={16} aria-hidden="true" />
      <span>{valor}</span>
      <span className="cds--visually-hidden">({TEXTO_SEMANTICA[semantica]})</span>
    </span>
  );
}
