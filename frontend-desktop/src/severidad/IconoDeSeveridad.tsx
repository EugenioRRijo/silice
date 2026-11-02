import { ErrorFilled, InformationFilled, WarningAltFilled, WarningFilled } from "@carbon/icons-react";
import type { ComponentType } from "react";
import type { NombreDeIcono } from "./severidad";

type Icono = ComponentType<{ size?: number; className?: string; "aria-hidden"?: boolean | "true" | "false"; "data-icono"?: string }>;

const ICONOS: Record<NombreDeIcono, Icono> = {
  ErrorFilled,
  WarningFilled,
  WarningAltFilled,
  InformationFilled,
};

// Icono decorativo: el significado lo da siempre el texto que lo acompana. `data-icono` deja probar cual es.
// El glifo del triangulo amarillo se oscurece por CSS (.icono-sev, ver tipografia de severidad en visor.scss).
export function IconoDeSeveridad({ nombre, size = 16, className }: { nombre: NombreDeIcono; size?: number; className?: string }) {
  const Componente = ICONOS[nombre];
  return (
    <Componente
      size={size}
      className={className ? `icono-sev ${className}` : "icono-sev"}
      aria-hidden="true"
      data-icono={nombre}
    />
  );
}
