import { CheckmarkOutline } from "@carbon/icons-react";
import { Button } from "@carbon/react";
import { useContext } from "react";
import { Severidad } from "../../comun/Severidad";
import { ContextoAuditoria } from "./ContextoAuditoria";
import type { EstadoFila } from "./logica";

interface Props {
  estado: EstadoFila;
  // Con ellos, y si la fila tiene algún hallazgo, se ofrece «Ver en Auditoría» (los orígenes con que se buscan y el
  // nombre de la fila).
  claves?: string[];
  rotulo?: string;
}

// El Estado de una fila: ícono y nombre de la severidad (el color nunca va solo) y el texto completo, que envuelve.
export function EstadoDeFila({ estado, claves, rotulo }: Props) {
  const verEnAuditoria = useContext(ContextoAuditoria);
  if (estado.severidad === null) {
    return (
      <span className="silice-hoja__estado-fila" title={estado.texto}>
        <span className="silice-sev--celda">
          <CheckmarkOutline size={16} aria-hidden="true" />
          <span>{estado.texto}</span>
        </span>
      </span>
    );
  }
  return (
    <span className="silice-hoja__estado-fila" title={estado.texto}>
      <Severidad valor={estado.severidad} />
      <span className="silice-hoja__estado-texto">{estado.texto}</span>
      {verEnAuditoria !== null && claves !== undefined && rotulo !== undefined && (
        <Button
          kind="ghost"
          size="sm"
          aria-label={`Ver en Auditoría: ${rotulo}`}
          onClick={() => verEnAuditoria({ claves, rotulo })}
        >
          Ver en Auditoría
        </Button>
      )}
    </span>
  );
}
