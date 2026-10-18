import { ErrorFilled, InformationFilled, WarningAltFilled, WarningFilled } from "@carbon/icons-react";
import type { ComponentType } from "react";
import type { NombreDeIcono } from "./halos";

type Icono = ComponentType<{ size?: number; className?: string; "aria-hidden"?: boolean | "true" | "false" }>;

const ICONOS: Record<NombreDeIcono, Icono> = {
  ErrorFilled,
  WarningFilled,
  WarningAltFilled,
  InformationFilled,
};

// Icono decorativo: el significado lo da siempre el texto que lo acompana.
export function IconoDeSeveridad({ nombre, size = 16, className }: { nombre: NombreDeIcono; size?: number; className?: string }) {
  const Componente = ICONOS[nombre];
  return <Componente size={size} className={className} aria-hidden="true" />;
}
