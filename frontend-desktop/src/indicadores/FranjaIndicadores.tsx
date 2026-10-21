import { esLibroMenor } from "./ibcs";
import { IndicadorFiori } from "./IndicadorFiori";
import type { IndicadorRespuesta } from "./tipos";

interface Props {
  indicadores: IndicadorRespuesta[];
  // El exacto de cada total, por la misma clave que el indicador (SUBSINIVA, IVATOT, TOTALGEN).
  totalesLibro?: Record<string, string>;
  totalesSilice?: Record<string, string>;
  rotuloMeta?: string;
  // V-16: partidas con el costo directo incompleto (L4), para la etiqueta del libro menor.
  partidasConOmision?: readonly number[];
}

// Franja bajo la cabecera: indicadores separados por divisores de 1 px, con un alto minimo de 4 rem que crece solo si un
// indicador lleva la etiqueta del libro menor (V-16): la completa en «Total general» (o en el primer indicador menor si
// ese no lo es) y un marcador de un renglon en los demas. Los textos de la tarjeta se recortan con elipsis (el valor
// completo queda en el tooltip y en el texto accesible). Los conteos por severidad no estan aqui: salen una sola vez,
// en los filtros de la lista de hallazgos.
export function FranjaIndicadores({ indicadores, totalesLibro, totalesSilice, rotuloMeta, partidasConOmision }: Props) {
  const menores = indicadores.filter((i) => esLibroMenor(i.delta, i.sentido));
  const conFrase = (menores.find((i) => i.clave === "TOTALGEN") ?? menores[0])?.clave;
  return (
    <section className="franja-indicadores" aria-label="Indicadores del libro">
      <div className="franja-indicadores__lista">
        {indicadores.map((i) => (
          <IndicadorFiori
            key={i.clave}
            indicador={i}
            exactoLibro={totalesLibro?.[i.clave]}
            exactoSilice={totalesSilice?.[i.clave]}
            rotuloMeta={rotuloMeta}
            partidasConOmision={partidasConOmision}
            etiquetaBreve={i.clave !== conFrase}
          />
        ))}
      </div>
    </section>
  );
}
