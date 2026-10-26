import { SkeletonText } from "@carbon/react";
import { useId } from "react";
import type { JSX } from "react";
import { IndicadorFiori } from "../../indicadores/IndicadorFiori";
import type { Carga } from "../inicio/useCarga";
import { textoConversion, textoFueraDeSuma } from "./logica";
import type { ResumenObrasRespuesta } from "./logica";

// Cuantas cifras puede mandar hoy `GET /v1/obras/resumen` (valor ganado y avance): el esqueleto dibuja esa forma para
// que nada salte al llegar los datos. «Por aprobar» (diseno de modulos §12.6) se sumara cuando la API la sirva.
const CIFRAS_DEL_RESUMEN = 2;

// «Cómo van las obras»: la franja de cifras Fiori (valor, meta y desviacion juntos; la variacion con su palabra y su
// flecha, IBCS) de las obras en ejecucion, y debajo lo que hay que saber para leerlas: que obra se convirtio y con que
// tasa, y cual no se sumo. Las cifras salen todas de la API. Un 403 o un fallo del resumen no pintan el bloque: el
// aviso del fallo va una sola vez, en el bloque de las obras (las dos salen de la misma respuesta).
export function CifrasMesa({ carga }: { carga: Carga<ResumenObrasRespuesta> }): JSX.Element | null {
  const idTitulo = useId();
  if (carga.estado !== "cargando" && carga.estado !== "listo") return null;
  // Sin obras no hay nada que sumar: el bloque de las obras dice que hacer.
  if (carga.estado === "listo" && carga.datos.obras.length === 0) return null;

  return (
    <section className="silice-mesa__bloque" aria-labelledby={idTitulo}>
      <h2 id={idTitulo} className="cds--type-heading-compact-02">
        Cómo van las obras
      </h2>
      {carga.estado === "cargando" ? <Esqueleto /> : <Cifras resumen={carga.datos} />}
    </section>
  );
}

function Esqueleto() {
  return (
    <div className="silice-mesa__franja" role="status" aria-busy="true" aria-label="Cargando las cifras de las obras">
      {Array.from({ length: CIFRAS_DEL_RESUMEN }, (_, i) => (
        <div key={i} className="silice-mesa__cifra silice-mesa__cifra--esqueleto">
          <SkeletonText width="45%" />
          <SkeletonText heading width="60%" />
        </div>
      ))}
    </div>
  );
}

function Cifras({ resumen }: { resumen: ResumenObrasRespuesta }) {
  const fuera = textoFueraDeSuma(resumen.fuera_de_suma);
  const hayNotas = resumen.conversiones.length > 0 || fuera !== null;
  return (
    <>
      {resumen.cifras.length > 0 ? (
        <div className="silice-mesa__franja">
          {resumen.cifras.map((cifra) => (
            <div key={cifra.clave} className="silice-mesa__cifra">
              <IndicadorFiori indicador={cifra} rotuloMeta="Meta" />
              {cifra.detalle && <p className="silice-mesa__detalle cds--type-body-compact-01">{cifra.detalle}</p>}
            </div>
          ))}
        </div>
      ) : (
        <p className="silice-mesa__nota cds--type-body-compact-01">
          Aún no hay obras en ejecución que sumar. Cuando una obra tenga su línea base declarada en Control de obra,
          aquí verá su valor ganado contra lo planificado.
        </p>
      )}
      {hayNotas && (
        <ul className="silice-mesa__notas cds--type-body-compact-01">
          {resumen.conversiones.map((c) => (
            <li key={`${c.obra}-${c.fecha_tasa}`}>{textoConversion(c, resumen.moneda)}</li>
          ))}
          {fuera !== null && <li className="silice-mesa__nota--fuera">{fuera}</li>}
        </ul>
      )}
    </>
  );
}
