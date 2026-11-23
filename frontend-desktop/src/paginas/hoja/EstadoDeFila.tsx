import { CheckmarkOutline } from "@carbon/icons-react";
import { Button } from "@carbon/react";
import { useContext } from "react";
import { Severidad } from "../../comun/Severidad";
import { cifrasEnTextoEsVe } from "../../indicadores/formatoEsVe";
import { ContextoAuditoria } from "./ContextoAuditoria";
import { estadoLlano } from "./estadoLlano";
import type { EstadoFila } from "./logica";

interface Props {
  estado: EstadoFila;
  // Con ellos, y si la fila tiene algún hallazgo, se ofrece «Ver en Revisión» (los orígenes con que se buscan y el
  // nombre de la fila).
  claves?: string[];
  rotulo?: string;
}

// El Estado de una fila: ícono y nombre de la severidad (el color nunca va solo) y el texto completo, que envuelve. El
// texto lo escriben las reglas del núcleo con punto decimal («(1.89 m3)»): se lee en es-VE (prueba en vivo del 18/11/2026).
export function EstadoDeFila({ estado, claves, rotulo }: Props) {
  const verEnRevision = useContext(ContextoAuditoria);
  // Sin la severidad repetida en mayúsculas y con los avisos conocidos del núcleo en español llano (`estadoLlano`).
  const texto = estadoLlano(cifrasEnTextoEsVe(estado.texto), estado.severidad);
  if (estado.severidad === null) {
    return (
      <span className="silice-hoja__estado-fila" title={texto}>
        <span className="silice-sev--celda">
          <CheckmarkOutline size={16} aria-hidden="true" />
          <span>{texto}</span>
        </span>
      </span>
    );
  }
  return (
    <span className="silice-hoja__estado-fila" title={texto}>
      <Severidad valor={estado.severidad} />
      <span className="silice-hoja__estado-texto">{texto}</span>
      {verEnRevision !== null && claves !== undefined && rotulo !== undefined && (
        <Button
          kind="ghost"
          size="sm"
          aria-label={`Ver en Revisión: ${rotulo}`}
          onClick={() => verEnRevision({ claves, rotulo })}
        >
          Ver en Revisión
        </Button>
      )}
    </span>
  );
}
