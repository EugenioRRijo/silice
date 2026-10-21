import { CaretDown, CaretUp } from "@carbon/icons-react";
import { Tooltip } from "@carbon/react";
import { useId } from "react";
import { EtiquetaLibroMenor } from "./EtiquetaLibroMenor";
import { formatoEsVe } from "./formatoEsVe";
import { esLibroMenor, haySubida, semanticaIbcs, TEXTO_SEMANTICA } from "./ibcs";
import type { IndicadorRespuesta } from "./tipos";

interface Props {
  indicador: IndicadorRespuesta;
  // El valor exacto del total (de totales_libro / totales_silice): la API manda los montos en centesimas.
  exactoLibro?: string;
  exactoSilice?: string;
  // Rotulo de la referencia: «Meta» para el Tablero; el Libro la rotula «Según Sílice» (V-15).
  rotuloMeta?: string;
  // V-16: numeros de las partidas con el costo directo incompleto (L4). Solo se usa si el indicador es «libro menor».
  partidasConOmision?: readonly number[];
  // Subtotal e IVA: solo el marcador «Libro menor» (la frase completa va en «Total general»).
  etiquetaBreve?: boolean;
}

// Proporciones solo para dibujar la barra (no es dinero): real y meta contra el mayor de los dos. Sin barra si la
// variacion no se ve.
function proporciones(actual: string, meta: string): { real: number; meta: number } | null {
  const a = Number(actual);
  const m = Number(meta);
  if (!Number.isFinite(a) || !Number.isFinite(m) || a < 0 || m < 0) return null;
  const tope = Math.max(a, m);
  if (tope === 0) return null;
  // Una diferencia menor a 2 % no se distingue en una barra de 150 px: se quita en vez de dibujar dos barras iguales.
  if (Math.abs(a - m) / tope < 0.02) return null;
  return { real: (a / tope) * 100, meta: (m / tope) * 100 };
}

// Patron SAP Fiori: valor actual, meta y desviacion. Los montos se presentan en es-VE (4.358,21) sobre el
// texto decimal de la API, sin pasar por numero. El exacto de los dos totales (tambien en es-VE, sin redondear) va
// en un Tooltip de Carbon que se abre con el foco del teclado y con el raton, y es la descripcion accesible.
export function IndicadorFiori({ indicador, exactoLibro, exactoSilice, rotuloMeta = "Meta", partidasConOmision, etiquetaBreve = false }: Props) {
  const { titulo, actual, meta, delta, delta_pct: deltaPct, sentido } = indicador;
  const semantica = semanticaIbcs(delta, sentido);
  const barra = proporciones(actual, meta);
  const sube = haySubida(delta);
  const hayExacto = exactoLibro !== undefined || exactoSilice !== undefined;
  // V-16: el verde del libro menor lleva su etiqueta. El nombre del grupo es el titulo y la etiqueta es su descripcion
  // accesible (aria-describedby): la lectora la dice una vez, con la cifra, no dos.
  const libroMenor = esLibroMenor(delta, sentido);
  const idEtiqueta = useId();

  return (
    <div className={libroMenor && !etiquetaBreve ? "fiori-kpi fiori-kpi--frase" : "fiori-kpi"} role="group" aria-label={titulo} aria-describedby={libroMenor ? idEtiqueta : undefined}>
      <div className="fiori-kpi__fila">
        <span className="fiori-kpi__titulo cds--type-label-01">{titulo}</span>
        <span className="fiori-kpi__meta cds--type-label-01 silice-cifra">
          {rotuloMeta} <span>{formatoEsVe(meta)}</span>
        </span>
      </div>
      <div className="fiori-kpi__fila">
        {hayExacto ? (
          <Tooltip
            className="fiori-kpi__actual fiori-kpi__tooltip cds--type-heading-03 silice-cifra"
            align="bottom-start"
            description={
              <span className="fiori-kpi__exacto">
                {exactoLibro !== undefined && <span>{`En el libro: ${formatoEsVe(exactoLibro)}`}</span>}
                {exactoSilice !== undefined && <span>{`Según Sílice: ${formatoEsVe(exactoSilice)}`}</span>}
              </span>
            }
          >
            <button type="button" className="fiori-kpi__valor">
              {formatoEsVe(actual)}
            </button>
          </Tooltip>
        ) : (
          <span className="fiori-kpi__actual cds--type-heading-03 silice-cifra">{formatoEsVe(actual)}</span>
        )}
        <span className={`fiori-kpi__delta cds--type-label-01 silice-cifra ibcs-${semantica}`}>
          {semantica !== "neutro" &&
            (sube ? (
              <CaretUp size={16} aria-hidden="true" data-sentido="sube" />
            ) : (
              <CaretDown size={16} aria-hidden="true" data-sentido="baja" />
            ))}
          <span className="fiori-kpi__delta-texto">
            <span className="fiori-kpi__semantica">{TEXTO_SEMANTICA[semantica]}</span>{" "}
            Δ {formatoEsVe(delta)}
            {deltaPct !== null ? ` (${formatoEsVe(deltaPct)} %)` : ""}
          </span>
        </span>
      </div>
      {libroMenor && <EtiquetaLibroMenor partidas={partidasConOmision} breve={etiquetaBreve} id={idEtiqueta} />}
      {barra && (
        <span className="fiori-kpi__barra" aria-hidden="true">
          <span className="fiori-kpi__barra-real" style={{ inlineSize: `${barra.real}%` }} />
          <span className="fiori-kpi__barra-meta" style={{ inlineSize: `${barra.meta}%` }} />
        </span>
      )}
    </div>
  );
}
