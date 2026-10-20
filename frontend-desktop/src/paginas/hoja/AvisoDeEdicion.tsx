import { Button, InlineNotification } from "@carbon/react";
import type { ReactNode } from "react";
import type { EnvioDeSeccion, ErrorDeSeccion } from "./useEdicionDeSeccion";

// Lo que se dice mientras el borrador del servidor recibe lo escrito (región viva: se anuncia sin mover el foco).
export function AvisoDeEnvio({ envio }: { envio: EnvioDeSeccion }) {
  return (
    <p className="cds--type-helper-text-01" aria-live="polite">
      {envio === "quieto" ? "" : "Aplicando los cambios al borrador…"}
    </p>
  );
}

interface Props {
  error: Pick<ErrorDeSeccion<unknown>, "tipo" | "mensaje">;
  // Las celdas inválidas lo tienen como descripción accesible.
  id: string;
  alRecargar: () => void;
  alReabrir: () => void;
  // Botones propios de la sección (por ejemplo «Ir a la partida X»).
  children?: ReactNode;
}

// El aviso de un fallo al editar: el `detalle` del servidor tal cual (con la frase de la clásica en un 422) y, según el
// caso, «Recargar el borrador» (el `rev` es viejo) o «Abrir de nuevo» (el caso cambió o el borrador ya se guardó).
export function AvisoDeEdicion({ error, id, alRecargar, alReabrir, children }: Props) {
  return (
    <div id={id} className="silice-hoja__aviso-edicion">
      <InlineNotification
        kind={error.tipo === "conflicto" || error.tipo === "perdido" ? "warning" : "error"}
        role="alert"
        lowContrast
        hideCloseButton
        title={error.tipo === "conflicto" ? "El borrador cambió" : error.tipo === "perdido" ? "Este borrador ya no sirve" : "No se aplicó el cambio"}
        subtitle={error.mensaje}
      />
      {error.tipo === "conflicto" && (
        <Button kind="tertiary" size="sm" onClick={alRecargar}>
          Recargar el borrador
        </Button>
      )}
      {error.tipo === "perdido" && (
        <Button kind="tertiary" size="sm" onClick={alReabrir}>
          Abrir de nuevo
        </Button>
      )}
      {children}
    </div>
  );
}
