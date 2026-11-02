import { CheckmarkFilled, ErrorFilled } from "@carbon/icons-react";
import { useId } from "react";
import { AvisoError } from "../../comun/AvisoError";
import { useAplicacion } from "../../shell/contexto";
import { useCarga } from "../inicio/useCarga";
import { esCadena, rutaDeCadena } from "./logicaVersiones";
import type { CadenaRespuesta } from "./logicaVersiones";

// El estado de la cadena de sellos del proyecto (S6, RF-83): recalcula cada huella. Es una mejora declarada sobre la clásica
// (DV-7). Ícono y texto: el color nunca va solo. Si no se puede leer, lo dice sin romper el resto de la pestaña.
export function EstadoDeLaCadena({ proyecto }: { proyecto: string }) {
  const { alExpirar } = useAplicacion();
  const titulo = useId();
  const cadena = useCarga<CadenaRespuesta>(rutaDeCadena(proyecto), alExpirar);
  return (
    <section className="silice-hoja__seccion" aria-labelledby={titulo}>
      <h2 id={titulo} className="cds--type-heading-compact-02">
        Cadena de sellos
      </h2>
      {cadena.estado === "cargando" && (
        <p className="cds--type-helper-text-01" aria-live="polite">
          Leyendo la cadena…
        </p>
      )}
      {(cadena.estado === "error" || cadena.estado === "sin_permiso" || cadena.estado === "no_disponible") && (
        <AvisoError error={cadena.error} titulo="No se pudo leer la cadena de sellos" />
      )}
      {cadena.estado === "listo" && !esCadena(cadena.datos) && (
        <AvisoError error="La respuesta de la cadena de sellos no tiene la forma esperada." titulo="No se pudo leer la cadena de sellos" />
      )}
      {cadena.estado === "listo" && esCadena(cadena.datos) && (
        <div className="silice-hoja__cadena">
          <p className="cds--type-body-compact-01 silice-hoja__cadena-estado" role="status">
            {cadena.datos.integra ? (
              <CheckmarkFilled size={16} aria-hidden="true" className="silice-hoja__cadena-integra" />
            ) : (
              <ErrorFilled size={16} aria-hidden="true" className="silice-hoja__cadena-rota" />
            )}
            <strong>{cadena.datos.integra ? "Cadena íntegra" : "Cadena rota"}</strong>
          </p>
          <p className="cds--type-body-compact-01">{cadena.datos.mensaje}</p>
          {typeof cadena.datos.declaracion === "string" && <p className="cds--type-helper-text-01">{cadena.datos.declaracion}</p>}
        </div>
      )}
    </section>
  );
}
