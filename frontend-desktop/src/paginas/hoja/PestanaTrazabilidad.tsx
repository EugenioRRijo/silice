import { TablaPaginada } from "./TablaPaginada";
import { VistaCarga } from "./VistaCarga";
import { fechaCorta, rotuloDeOrigen, rutaDeTrazabilidad } from "./logica";
import type { TrazabilidadRespuesta } from "./logica";

interface Props {
  proyecto: string;
  // null = borrador en blanco: no hay versión guardada de la que ver el historial.
  version: string | null;
  alAusente: () => void;
}

const SIN_VERSION = "Abra una versión guardada para ver su historial y sus registros de cambio.";

function ContenidoTrazabilidad({ vista, version }: { vista: TrazabilidadRespuesta; version: string }) {
  const titulo = `Registro de cambios de la versión ${version}`;
  return (
    <div className="silice-hoja__pestana">
      <section className="silice-hoja__seccion">
        <h2 className="cds--type-heading-compact-02">Versiones del proyecto</h2>
        <TablaPaginada
          etiqueta="Versiones del proyecto"
          desplazable
          columnas={[
            { clave: "codigo", titulo: "Versión", ordenable: false },
            { clave: "fecha", titulo: "Fecha", ordenable: false, presentar: fechaCorta },
            { clave: "motivo", titulo: "Motivo", ordenable: false },
            { clave: "origen", titulo: "Sale de", ordenable: false },
            { clave: "cambios", titulo: "Cambios", numerica: true, ordenable: false },
            { clave: "vigente", titulo: "Vigente", ordenable: false },
          ]}
          filas={vista.versiones.map((v) => ({
            id: `version-${v.codigo}`,
            codigo: v.codigo,
            fecha: v.fecha,
            motivo: v.motivo === "" ? "elaborada" : v.motivo,
            origen: v.origen,
            cambios: String(v.cambios),
            vigente: v.vigente ? "Sí" : "",
          }))}
        />
      </section>
      <section className="silice-hoja__seccion">
        <h2 className="cds--type-heading-compact-02">{titulo}</h2>
        {vista.registros.length === 0 ? (
          <p className="cds--type-body-compact-01">{vista.vacio_mensaje}</p>
        ) : (
          <TablaPaginada
            etiqueta={titulo}
            desplazable
            columnas={[
              { clave: "objeto", titulo: "Objeto", ordenable: false },
              {
                clave: "clave",
                titulo: "Clave",
                ordenable: false,
                celda: (f) => <span title={f.clave}>{rotuloDeOrigen(f.clave!)}</span>,
              },
              { clave: "campo", titulo: "Campo", ordenable: false },
              { clave: "antes", titulo: "Antes", ordenable: false },
              { clave: "despues", titulo: "Después", ordenable: false },
              { clave: "fuente", titulo: "Fuente", ordenable: false },
              { clave: "responsable", titulo: "Responsable", ordenable: false },
              { clave: "fecha_hora", titulo: "Fecha y hora", ordenable: false, presentar: fechaCorta },
            ]}
            filas={vista.registros.map((r, i) => ({
              id: `registro-${i}`,
              objeto: r.objeto,
              clave: r.clave,
              campo: r.campo,
              antes: r.antes,
              despues: r.despues,
              fuente: r.fuente,
              responsable: r.responsable,
              fecha_hora: r.fecha_hora,
            }))}
          />
        )}
      </section>
    </div>
  );
}

// Pestaña «Trazabilidad»: las versiones del proyecto y el registro de cambios de la versión abierta (guardada). Restaurar
// una versión llega en la rebanada 3d.
export function PestanaTrazabilidad({ proyecto, version, alAusente }: Props) {
  if (version === null) return <p className="cds--type-body-compact-01">{SIN_VERSION}</p>;
  return (
    <VistaCarga<TrazabilidadRespuesta> ruta={rutaDeTrazabilidad(proyecto, version)} etiqueta="Trazabilidad" alAusente={alAusente}>
      {(vista) => <ContenidoTrazabilidad vista={vista} version={version} />}
    </VistaCarga>
  );
}
