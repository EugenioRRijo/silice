import { WarningAltFilled } from "@carbon/icons-react";
import { SkeletonText } from "@carbon/react";
import { useId } from "react";
import type { JSX } from "react";
import { IndicadorFiori } from "../../indicadores/IndicadorFiori";
import type { Carga } from "../inicio/useCarga";
import { textoConversion, textoFueraDeSuma } from "./logica";
import type { CifraPorAprobar, CifraRespuesta, ResumenObrasRespuesta } from "./logica";

// Cuantas cifras manda `GET /v1/obras/resumen` (valor ganado y avance), mas «Por aprobar» (diseno de modulos §12.6, de
// `GET /v1/aprobaciones/resumen`, Tarea 19) si la cuenta puede aprobar: el esqueleto dibuja esa forma para que nada salte
// al llegar los datos.
const CIFRAS_DEL_RESUMEN = 2;
const CIFRAS_CON_POR_APROBAR = 3;

// La marca de «Por aprobar» (la pone la API desde 3 dias habiles de espera de la mas antigua): icono y texto, nunca solo
// color (la etiqueta de advertencia pegada de DESIGN.md).
const MARCA_POR_APROBAR = "Hay versiones esperando dictamen desde hace días: revíselas pronto.";

interface Props {
  carga: Carga<ResumenObrasRespuesta>;
  // La cifra «Por aprobar»; `sin_permiso` si la cuenta no aprueba versiones o la API dio 403: no se pinta.
  porAprobar: Carga<CifraPorAprobar>;
}

// «Cómo van las obras»: la franja de cifras Fiori (valor, meta y desviacion juntos; la variacion con su palabra y su
// flecha, IBCS) de las obras en ejecucion y lo que espera dictamen, y debajo lo que hay que saber para leerlas: que obra
// se convirtio y con que tasa, y cual no se sumo. Las cifras salen todas de la API. Un 403 o un fallo del resumen no
// pintan el bloque: el aviso del fallo va una sola vez, en el bloque de las obras (las dos salen de la misma respuesta).
// «Por aprobar» va aparte: un 403 o un fallo suyo la quitan de la franja sin tocar las demas (lo que espera dictamen
// tambien se lee en el grupo «Aprobar» de los pendientes).
export function CifrasMesa({ carga, porAprobar }: Props): JSX.Element | null {
  const idTitulo = useId();
  if (carga.estado !== "cargando" && carga.estado !== "listo") return null;
  const aprobar = porAprobar.estado === "listo" ? porAprobar.datos : null;
  // Sin obras no hay nada que sumar (el bloque de las obras dice que hacer); lo que espera dictamen, que es de todas las
  // carpetas, si se dice.
  if (carga.estado === "listo" && carga.datos.obras.length === 0 && aprobar === null) return null;

  return (
    <section className="silice-mesa__bloque" aria-labelledby={idTitulo}>
      <h2 id={idTitulo} className="cds--type-heading-compact-02">
        Cómo van las obras
      </h2>
      {carga.estado === "cargando" ? (
        <Esqueleto cuantas={porAprobar.estado === "sin_permiso" ? CIFRAS_DEL_RESUMEN : CIFRAS_CON_POR_APROBAR} />
      ) : (
        <Cifras resumen={carga.datos} aprobar={aprobar} />
      )}
    </section>
  );
}

function Esqueleto({ cuantas }: { cuantas: number }) {
  return (
    <div className="silice-mesa__franja" role="status" aria-busy="true" aria-label="Cargando las cifras de las obras">
      {Array.from({ length: cuantas }, (_, i) => (
        <div key={i} className="silice-mesa__cifra silice-mesa__cifra--esqueleto">
          <SkeletonText width="45%" />
          <SkeletonText heading width="60%" />
        </div>
      ))}
    </div>
  );
}

function Cifras({ resumen, aprobar }: { resumen: ResumenObrasRespuesta; aprobar: CifraPorAprobar | null }) {
  const fuera = textoFueraDeSuma(resumen.fuera_de_suma);
  const hayNotas = resumen.conversiones.length > 0 || fuera !== null;
  const cifras: Array<CifraRespuesta & { marcada?: boolean }> = aprobar === null ? resumen.cifras : [...resumen.cifras, aprobar];
  return (
    <>
      {cifras.length > 0 && (
        <div className="silice-mesa__franja">
          {cifras.map((cifra) => (
            <Cifra key={cifra.clave} cifra={cifra} />
          ))}
        </div>
      )}
      {resumen.cifras.length === 0 && resumen.obras.length > 0 && (
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

// Una cifra con su linea de debajo y, si la API la marca, el aviso pegado. Las dos son parte de la cifra: la lectora las
// dice con ella (descripcion del grupo).
function Cifra({ cifra }: { cifra: CifraRespuesta & { marcada?: boolean } }) {
  const base = useId();
  const idDetalle = cifra.detalle ? `${base}-detalle` : null;
  const idMarca = cifra.marcada === true ? `${base}-marca` : null;
  const descripcion = [idDetalle, idMarca].filter((id) => id !== null).join(" ");
  return (
    <div className="silice-mesa__cifra">
      <IndicadorFiori indicador={cifra} rotuloMeta="Meta" idDescripcion={descripcion || undefined} />
      {idDetalle && (
        <p id={idDetalle} className="silice-mesa__detalle cds--type-body-compact-01">
          {cifra.detalle}
        </p>
      )}
      {idMarca && (
        <p id={idMarca} role="note" className="fiori-kpi__aviso silice-mesa__marca cds--type-label-01">
          <WarningAltFilled size={16} className="fiori-kpi__aviso-icono" aria-hidden="true" />
          <span className="fiori-kpi__aviso-texto">{MARCA_POR_APROBAR}</span>
        </p>
      )}
    </div>
  );
}
