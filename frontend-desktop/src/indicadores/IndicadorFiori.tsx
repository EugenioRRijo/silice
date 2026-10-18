import { CaretDown, CaretUp } from "@carbon/icons-react";
import { haySubida, semanticaIbcs, TEXTO_SEMANTICA } from "./ibcs";
import type { IndicadorRespuesta } from "./tipos";

interface Props {
  indicador: IndicadorRespuesta;
}

// Proporciones solo para dibujar la barra (no es dinero): real y meta contra el mayor de los dos.
function proporciones(actual: string, meta: string): { real: number; meta: number } | null {
  const a = Number(actual);
  const m = Number(meta);
  if (!Number.isFinite(a) || !Number.isFinite(m) || a < 0 || m < 0) return null;
  const tope = Math.max(a, m);
  if (tope === 0) return null;
  return { real: (a / tope) * 100, meta: (m / tope) * 100 };
}

// Patron SAP Fiori: valor actual, meta y desviacion. Los montos se muestran exactos, como llegan de la API.
export function IndicadorFiori({ indicador }: Props) {
  const { titulo, actual, meta, delta, delta_pct: deltaPct, sentido } = indicador;
  const semantica = semanticaIbcs(delta, sentido);
  const barra = proporciones(actual, meta);

  return (
    <div className="fiori-kpi" role="group" aria-label={titulo}>
      <span className="fiori-kpi__titulo cds--type-label-01">{titulo}</span>
      <span className="fiori-kpi__meta cds--type-label-01 silice-cifra">
        Meta <span>{meta}</span>
      </span>
      <span className="fiori-kpi__actual cds--type-heading-03 silice-cifra">{actual}</span>
      <span className={`fiori-kpi__delta cds--type-label-01 silice-cifra ibcs-${semantica}`}>
        {semantica !== "neutro" &&
          (haySubida(delta) ? (
            <CaretUp size={16} aria-hidden="true" />
          ) : (
            <CaretDown size={16} aria-hidden="true" />
          ))}
        <span className="silice-oculto">{TEXTO_SEMANTICA[semantica]}</span>
        <span>
          Δ {delta}
          {deltaPct !== null ? ` (${deltaPct} %)` : ""}
        </span>
      </span>
      {barra && (
        <span className="fiori-kpi__barra" aria-hidden="true">
          <span className="fiori-kpi__barra-real" style={{ inlineSize: `${barra.real}%` }} />
          <span className="fiori-kpi__barra-meta" style={{ inlineSize: `${barra.meta}%` }} />
        </span>
      )}
    </div>
  );
}
