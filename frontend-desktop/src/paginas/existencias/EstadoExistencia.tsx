import { CheckmarkFilled, ErrorFilled, WarningAltFilled } from "@carbon/icons-react";
import type { ComponentType } from "react";
import type { ExistenciaRespuesta } from "./tipos";

export type Estado = "normal" | "queda_poco" | "negativa";

export const ROTULOS_DE_ESTADO: Record<Estado, string> = {
  normal: "Normal",
  queda_poco: "Queda poco",
  negativa: "Existencia negativa: falta registrar producción o conteo",
};

type Icono = ComponentType<{ size?: number; className?: string; "aria-hidden"?: boolean | "true" | "false" }>;

// Severidad (no variacion): cada estado con su icono de Carbon y su texto; el color solo acompana.
const ICONOS: Record<Estado, Icono> = {
  normal: CheckmarkFilled,
  queda_poco: WarningAltFilled,
  negativa: ErrorFilled,
};

// La negativa manda sobre «queda poco»: con la existencia bajo cero la API marca las dos, y lo que importa decir es
// que falta registrar producción o un conteo.
export function estadoDe(fila: Pick<ExistenciaRespuesta, "queda_poco" | "negativa">): Estado {
  if (fila.negativa) return "negativa";
  return fila.queda_poco ? "queda_poco" : "normal";
}

export function EstadoExistencia({ estado }: { estado: Estado }) {
  const Icono = ICONOS[estado];
  return (
    <span className={`existencias-estado existencias-estado--${estado}`} data-estado={estado}>
      <Icono size={16} className="existencias-estado__icono" aria-hidden="true" />
      <span>{ROTULOS_DE_ESTADO[estado]}</span>
    </span>
  );
}
