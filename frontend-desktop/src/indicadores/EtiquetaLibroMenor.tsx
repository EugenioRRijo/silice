import { WarningAltFilled } from "@carbon/icons-react";

// Sin datos de omision: la frase fija, sin numeros (no se inventa nada que la API no sepa).
export const TEXTO_LIBRO_MENOR_FIJO = "Libro menor: puede deberse a partidas omitidas; revise antes de aceptar";

const MAXIMO_LISTADAS = 5;

// Con datos (la API manda los numeros de las partidas con un hallazgo L4, costo directo que deja componentes fuera):
// el numero real y cuales son (con espacio duro tras «n.º»: el numero no se separa de la abreviatura). Las primeras cinco; del resto solo la cuenta.
export function textoLibroMenor(partidas: readonly number[] | undefined): string {
  if (!partidas || partidas.length === 0) return TEXTO_LIBRO_MENOR_FIJO;
  const n = partidas.length;
  const listadas = partidas.slice(0, MAXIMO_LISTADAS).join(", ");
  const resto = n > MAXIMO_LISTADAS ? ` y ${n - MAXIMO_LISTADAS} más` : "";
  return `Libro menor: revise si omite ${n} ${n === 1 ? "partida" : "partidas"} (n.º\u00a0${listadas}${resto})`;
}

interface Props {
  partidas?: readonly number[];
}

// Etiqueta de advertencia pegada (DESIGN.md): va dentro del indicador, junto a la cifra, siempre visible, con icono y
// texto, sin boton de cierre ni tooltip. Su texto tambien entra en el nombre accesible del indicador (IndicadorFiori).
export function EtiquetaLibroMenor({ partidas }: Props) {
  return (
    <span className="fiori-kpi__aviso cds--type-label-01" role="note">
      <WarningAltFilled size={16} className="fiori-kpi__aviso-icono" aria-hidden="true" />
      <span className="fiori-kpi__aviso-texto">{textoLibroMenor(partidas)}</span>
    </span>
  );
}
