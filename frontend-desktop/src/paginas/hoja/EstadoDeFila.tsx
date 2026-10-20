import { CheckmarkOutline } from "@carbon/icons-react";
import { Severidad } from "../../comun/Severidad";
import type { EstadoFila } from "./logica";

// El Estado de una fila: ícono y nombre de la severidad (el color nunca va solo) y el texto recortado; completo en el title.
export function EstadoDeFila({ estado }: { estado: EstadoFila }) {
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
    </span>
  );
}
