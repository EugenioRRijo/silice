import { WarningAltFilled } from "@carbon/icons-react";

// Sin datos de omision: la frase fija, sin numeros (no se inventa nada que la API no sepa).
export const TEXTO_LIBRO_MENOR_FIJO = "Libro menor: puede deberse a partidas omitidas; revise antes de aceptar";

// Marcador breve (subtotal e IVA): mismo icono y mismos tokens; la frase completa va en «Total general».
export const TEXTO_LIBRO_MENOR_BREVE = "Libro menor";

const MAXIMO_LISTADAS = 5;

// Con datos la API manda los numeros de las partidas cuyo APU tiene un hallazgo L4: partidas PRESENTES cuyo costo
// directo deja componentes fuera o no es la suma. No son partidas ausentes: de esas el comparador no sabe nada, y por
// eso la frase lo avisa. Las primeras cinco; del resto solo la cuenta. Espacio duro tras «n.º»: el numero no se parte
// de la abreviatura.
export function textoLibroMenor(partidas: readonly number[] | undefined): string {
  if (!partidas || partidas.length === 0) return TEXTO_LIBRO_MENOR_FIJO;
  const n = partidas.length;
  const listadas = partidas.slice(0, MAXIMO_LISTADAS).join(", ");
  const resto = n > MAXIMO_LISTADAS ? ` y ${n - MAXIMO_LISTADAS} más` : "";
  const cuantas = n === 1 ? "1 partida" : `${n} partidas`;
  return `Libro menor: ${cuantas} con costo directo incompleto (n.º ${listadas}${resto}). Puede faltar además alguna partida; revise antes de aceptar`;
}

interface Props {
  partidas?: readonly number[];
  // Marcador de un renglon («Libro menor»), sin la frase completa.
  breve?: boolean;
  // Para que el indicador la use como descripcion accesible (aria-describedby).
  id?: string;
}

// Etiqueta de advertencia pegada (DESIGN.md): va dentro del indicador, junto a la cifra, siempre visible, con icono y
// texto, sin boton de cierre ni tooltip.
export function EtiquetaLibroMenor({ partidas, breve = false, id }: Props) {
  return (
    <span className="fiori-kpi__aviso cds--type-label-01" role="note" id={id}>
      <WarningAltFilled size={16} className="fiori-kpi__aviso-icono" aria-hidden="true" />
      <span className="fiori-kpi__aviso-texto">{breve ? TEXTO_LIBRO_MENOR_BREVE : textoLibroMenor(partidas)}</span>
    </span>
  );
}
