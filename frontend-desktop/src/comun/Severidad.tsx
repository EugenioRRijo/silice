import { ErrorFilled, InformationFilled, WarningAltFilled, WarningFilled } from "@carbon/icons-react";
import type { ComponentType } from "react";

const MAPA: Record<string, { texto: string; clase: string; Icono: ComponentType<{ size?: number; className?: string }> }> = {
  CRITICO: { texto: "Crítico", clase: "critico", Icono: ErrorFilled },
  ERROR: { texto: "Error", clase: "error", Icono: WarningFilled },
  ADVERTENCIA: { texto: "Advertencia", clase: "advertencia", Icono: WarningAltFilled },
  INFO: { texto: "Información", clase: "info", Icono: InformationFilled },
};

// La severidad de un hallazgo (DESIGN.md: dos semanticas de color separadas): icono de Carbon con el color de su
// token y el nombre en texto. El color nunca va solo. Una severidad que la interfaz no conoce se muestra con su
// texto y el icono de informacion, sin inventar un color.
export function Severidad({ valor }: { valor: string }) {
  const def = MAPA[valor.toUpperCase()];
  const Icono = def?.Icono ?? InformationFilled;
  return (
    <span className={`silice-sev silice-sev--${def?.clase ?? "info"} silice-sev--celda`}>
      <Icono size={16} className="silice-sev__icono" />
      <span>{def?.texto ?? valor}</span>
    </span>
  );
}
