import { CheckmarkFilled, ErrorFilled } from "@carbon/icons-react";
import { AvisoError } from "../../comun/AvisoError";
import { useAplicacion } from "../../shell/contexto";
import { esCadena, rutaDeCadena } from "../hoja/logicaVersiones";
import type { CadenaRespuesta } from "../hoja/logicaVersiones";
import { useCarga } from "../../comun/useCarga";
import { TEXTOS_DE_VERSIONES as T } from "./textos";

// El estado de la cadena de sellos de la obra (S6, RF-83): recalcula cada huella. Es una mejora declarada sobre la clásica
// (DV-7). Desde la Tarea 6 del plan F4 es el aviso de encima de la tabla de Versiones (venía de la pestaña «Trazabilidad»):
// «Integridad verificada» o «Se rompió en la versión X» (`rota_en`, que da el servidor), con su ícono (el color nunca va
// solo), y debajo el texto del servidor. Si no se puede leer, lo dice sin romper la tabla.
export function EstadoDeLaCadena({ proyecto }: { proyecto: string }) {
  const { alExpirar } = useAplicacion();
  const cadena = useCarga<CadenaRespuesta>(rutaDeCadena(proyecto), alExpirar);
  return (
    <section className="silice-versiones__cadena" aria-label={T.cadena}>
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
      {cadena.estado === "listo" && esCadena(cadena.datos) && <Estado datos={cadena.datos} />}
    </section>
  );
}

function Estado({ datos }: { datos: CadenaRespuesta }) {
  return (
    <>
      <p className="cds--type-body-compact-01 silice-versiones__cadena-estado" role="status">
        {datos.integra ? (
          <CheckmarkFilled size={16} aria-hidden="true" className="silice-versiones__cadena-integra" />
        ) : (
          <ErrorFilled size={16} aria-hidden="true" className="silice-versiones__cadena-rota" />
        )}
        <strong>{datos.integra ? T.integra : T.rota(datos.rota_en ?? null)}</strong>
      </p>
      <p className="cds--type-body-compact-01">{datos.mensaje}</p>
      {typeof datos.declaracion === "string" && <p className="cds--type-helper-text-01">{datos.declaracion}</p>}
    </>
  );
}
