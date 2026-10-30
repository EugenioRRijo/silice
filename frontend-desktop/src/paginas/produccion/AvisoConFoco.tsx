import { InlineNotification } from "@carbon/react";
import { useEffect, useRef } from "react";
import type { JSX } from "react";

interface Props {
  aviso: string | null;
  alCerrar: () => void;
  // Algo que, al cambiar mientras el aviso sigue a la vista, vuelve a llevar el foco a él (la lista que llegó de nuevo).
  refoco?: unknown;
}

// El aviso de éxito de una acción (registrar, anular, publicar). El botón que la persona usó se va con su diálogo o con
// su fila, así que el foco pasa al aviso en vez de quedar en BODY; el aviso se cierra con su equis.
export function AvisoConFoco({ aviso, alCerrar, refoco }: Props): JSX.Element | null {
  const caja = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (aviso) caja.current?.focus();
  }, [aviso, refoco]);
  if (!aviso) return null;
  return (
    <div ref={caja} tabIndex={-1}>
      <InlineNotification
        kind="success"
        role="status"
        lowContrast
        title={aviso}
        onClose={() => {
          alCerrar();
          return false;
        }}
      />
    </div>
  );
}
