import { Tag } from "@carbon/react";
import { IconoDeSeveridad } from "../severidad/IconoDeSeveridad";
import { SEVERIDADES, estiloDeSeveridad } from "../severidad/severidad";
import { IndicadorFiori } from "./IndicadorFiori";
import type { ConteoPorSeveridad, IndicadorRespuesta } from "./tipos";

interface Props {
  indicadores: IndicadorRespuesta[];
  porSeveridad: ConteoPorSeveridad;
  // El exacto de cada total, por la misma clave que el indicador (SUBSINIVA, IVATOT, TOTALGEN).
  totalesLibro?: Record<string, string>;
  totalesSilice?: Record<string, string>;
}

// Franja de 64 px bajo la cabecera: indicadores separados por divisores de 1 px y, al final, los conteos de
// hallazgos por severidad. Nunca crece mas de su alto: los indicadores se recortan con elipsis (el valor completo
// queda en el title y en texto accesible) y los conteos no se encogen. Un conteo no es una variacion: no lleva
// colores IBCS.
export function FranjaIndicadores({ indicadores, porSeveridad, totalesLibro, totalesSilice }: Props) {
  return (
    <section className="franja-indicadores" aria-label="Indicadores del libro">
      <div className="franja-indicadores__lista">
        {indicadores.map((i) => (
          <IndicadorFiori
            key={i.clave}
            indicador={i}
            exactoLibro={totalesLibro?.[i.clave]}
            exactoSilice={totalesSilice?.[i.clave]}
          />
        ))}
      </div>
      <div className="franja-indicadores__severidad" role="group" aria-label="Hallazgos por severidad">
        {SEVERIDADES.map((clave) => {
          const estilo = estiloDeSeveridad(clave);
          return (
            <Tag key={clave} size="md" type="outline" className={`silice-sev silice-sev--${clave.toLowerCase()}`}>
              <IconoDeSeveridad nombre={estilo.icono} size={16} className="silice-sev__icono" />
              <span>{estilo.texto}</span>
              <span className="silice-cifra">{porSeveridad[clave]}</span>
            </Tag>
          );
        })}
      </div>
    </section>
  );
}
