import { InlineNotification } from "@carbon/react";
import { mensajeDeError } from "./errores";

interface Props {
  // ErrorDeApi, texto o cualquier cosa que haya capturado un catch; null/undefined = no hay aviso.
  error: unknown;
  titulo?: string;
  // Si se da, el aviso se puede cerrar.
  alCerrar?: () => void;
  className?: string;
}

// Error de la API con su `detalle` tal cual (DESIGN.md, Texto). El color nunca va solo: Carbon pone el icono.
export function AvisoError({ error, titulo = "No se pudo completar la acción", alCerrar, className }: Props) {
  if (error === null || error === undefined) return null;
  return (
    <InlineNotification
      kind="error"
      role="alert"
      title={titulo}
      subtitle={mensajeDeError(error)}
      lowContrast
      hideCloseButton={!alCerrar}
      onClose={() => {
        alCerrar?.();
        return false; // el padre decide si desaparece
      }}
      className={className}
    />
  );
}
