import { TablaPaginada } from "../hoja/TablaPaginada";
import { VistaCarga } from "../hoja/VistaCarga";
import { fechaCorta, rotuloDeOrigen, rutaDeTrazabilidad } from "../hoja/logica";
import type { TrazabilidadRespuesta } from "../hoja/logica";
import { TEXTOS_DE_VERSIONES as T } from "./textos";

// El registro de cambios de una versión guardada (`GET /v1/hoja/trazabilidad`): qué cambió, de qué a qué, con su fuente, su
// responsable y su hora. Era la pestaña «Trazabilidad» de la Hoja (baja 24); desde la Tarea 6 del plan F4 lo pinta el panel
// «Registro de cambios de la versión V» de Versiones. La lista de versiones que también trae la respuesta no se usa aquí: la
// tabla de Versiones sale de la lista del proveedor. Una versión que no nació de una edición dice por qué no tiene registros.
export function RegistroDeCambios({ proyecto, version, alAusente }: { proyecto: string; version: string; alAusente: () => void }) {
  return (
    <VistaCarga<TrazabilidadRespuesta> ruta={rutaDeTrazabilidad(proyecto, version)} etiqueta="el registro de cambios" alAusente={alAusente}>
      {(vista) => <Registros vista={vista} titulo={T.registro(version)} />}
    </VistaCarga>
  );
}

function Registros({ vista, titulo }: { vista: TrazabilidadRespuesta; titulo: string }) {
  if (vista.registros.length === 0) return <p className="cds--type-body-compact-01">{vista.vacio_mensaje}</p>;
  return (
    <TablaPaginada
      etiqueta={titulo}
      desplazable
      // Cuándo y quién primero, como en un registro de auditoría: al final quedaban fuera de la caja del panel (pasada de
      // navegador del cierre de F4, H5).
      columnas={[
        { clave: "fecha_hora", titulo: "Fecha y hora", ordenable: false, presentar: fechaCorta },
        { clave: "responsable", titulo: "Responsable", ordenable: false },
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
  );
}
