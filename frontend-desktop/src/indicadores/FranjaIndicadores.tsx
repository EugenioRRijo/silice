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

// Franja de 64 px bajo la cabecera: indicadores separados por divisores de 1 px. Solo crece si un indicador lleva la
// etiqueta del libro menor (V-16), que se ve completa. Fuera de eso no crece: los
// textos se recortan con elipsis (el valor completo queda en el tooltip y en el texto accesible). Los conteos por
// severidad no estan aqui: salen una sola vez, en los filtros de la lista de hallazgos.
export function FranjaIndicadores({ indicadores, totalesLibro, totalesSilice, rotuloMeta, partidasConOmision }: Props) {
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
          />
        ))}
      </div>
    </section>
  );
}
