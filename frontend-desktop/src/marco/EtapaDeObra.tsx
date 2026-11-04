import { CheckmarkOutline, Edit, InProgress, Time, WarningFilled } from "@carbon/icons-react";
import type { ComponentType } from "react";
import type { Etapa } from "../api/tipos";
import "./EtapaDeObra.scss";

// Un ícono por etapa (pregunta 11 del plan F4): lápiz mientras se elabora, reloj en aprobación, visto al aprobarse,
// avance en ejecución y advertencia si va atrasada. Carbon los trae todos; ninguno es un color suelto.
const ICONOS: Record<Etapa, ComponentType<{ size?: number; "aria-hidden"?: "true" }>> = {
  en_elaboracion: Edit,
  en_aprobacion: Time,
  aprobada: CheckmarkOutline,
  en_ejecucion: InProgress,
  atrasada: WarningFilled,
};

// La etapa de una obra: siempre la palabra que da el servidor (`etapa_texto`) y su ícono, decorativo. Existe porque la
// cabecera de la obra (Tarea 1 del plan F4) y las cifras del Resumen (Tarea 2) dicen lo mismo y no deben divergir; antes
// vivía como `Etapa` dentro de la tabla de obras, que usa ahora esta pieza.
export function EtapaDeObra({ etapa, texto }: { etapa: Etapa; texto: string }) {
  const Icono = ICONOS[etapa];
  return (
    <span className={etapa === "atrasada" ? "silice-etapa silice-etapa--atrasada" : "silice-etapa"}>
      {Icono !== undefined && <Icono size={16} aria-hidden="true" />}
      {texto}
    </span>
  );
}
