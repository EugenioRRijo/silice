import { Information } from "@carbon/icons-react";
import { Toggletip, ToggletipButton, ToggletipContent } from "@carbon/react";
import type { JSX } from "react";
import { formatoEsVe } from "../indicadores/formatoEsVe";

interface Props {
  texto: string;
  exacto: string;
  unidad?: string;
  enLinea?: boolean;
  nombre?: string;
}

// Presenta una cifra en es-VE y expone su valor exacto sin usar title: en un Toggletip accesible o en línea.
export function MontoExacto({ texto, exacto, unidad, enLinea = false, nombre }: Props): JSX.Element {
  const sufijo = unidad ? ` ${unidad}` : "";
  const vista = `${formatoEsVe(texto)}${sufijo}`;
  if (exacto === texto) {
    return <span className="silice-cifra">{vista}</span>;
  }
  const detalleExacto = `${formatoEsVe(exacto)}${sufijo}`;
  if (enLinea) {
    return <span className="silice-cifra">{`${vista} (exacto: ${detalleExacto})`}</span>;
  }
  const nombreLimpio = nombre?.trim();
  const etiquetaBoton = nombreLimpio ? `Ver el valor exacto ${nombreLimpio}` : `Ver el valor exacto de ${vista}`;
  return (
    <span>
      <span className="silice-cifra">{vista}</span>{" "}
      <Toggletip align="bottom">
        <ToggletipButton label={etiquetaBoton}>
          <Information size={16} aria-hidden="true" />
        </ToggletipButton>
        <ToggletipContent>
          <p>{`Valor exacto: ${detalleExacto}`}</p>
        </ToggletipContent>
      </Toggletip>
    </span>
  );
}
