import { ErrorFilled, InformationFilled, WarningAltFilled, WarningFilled } from "@carbon/icons-react";
import { Tag } from "@carbon/react";
import type { ComponentType } from "react";
import { IndicadorFiori } from "./IndicadorFiori";
import type { ConteoPorSeveridad, IndicadorRespuesta, Severidad } from "./tipos";

interface Props {
  indicadores: IndicadorRespuesta[];
  porSeveridad: ConteoPorSeveridad;
  rotuloMeta?: string;
}

const SEVERIDADES: {
  clave: Severidad;
  texto: string;
  Icono: ComponentType<{ size?: number; className?: string }>;
}[] = [
  { clave: "CRITICO", texto: "Crítico", Icono: ErrorFilled },
  { clave: "ERROR", texto: "Error", Icono: WarningFilled },
  { clave: "ADVERTENCIA", texto: "Advertencia", Icono: WarningAltFilled },
  { clave: "INFO", texto: "Información", Icono: InformationFilled },
];

// Franja densa de 64 px bajo la cabecera: indicadores separados por divisores de 1 px y, al final, los conteos
// de hallazgos por severidad. Un conteo no es una variacion: no lleva colores IBCS.
export function FranjaIndicadores({ indicadores, porSeveridad, rotuloMeta }: Props) {
  return (
    <section className="franja-indicadores" aria-label="Indicadores del libro">
      <div className="franja-indicadores__lista">
        {indicadores.map((i) => (
          <IndicadorFiori key={i.clave} indicador={i} rotuloMeta={rotuloMeta} />
        ))}
      </div>
      <div className="franja-indicadores__severidad" role="group" aria-label="Hallazgos por severidad">
        {SEVERIDADES.map(({ clave, texto, Icono }) => (
          <Tag key={clave} size="md" type="outline" className={`silice-sev silice-sev--${clave.toLowerCase()}`}>
            <Icono size={16} className="silice-sev__icono" />
            <span>{texto}</span>
            <span className="silice-cifra">{porSeveridad[clave]}</span>
          </Tag>
        ))}
      </div>
    </section>
  );
}
