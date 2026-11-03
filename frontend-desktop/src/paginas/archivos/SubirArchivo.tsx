import { Button } from "@carbon/react";
import { useCallback, useId, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createPortal } from "react-dom";
import { SubidaArchivo } from "../../comun/SubidaArchivo";
import type { Resumen } from "../hoja/logica";
import { useDialogo } from "../hoja/useDialogo";
import { ImportarPlano } from "./ImportarPlano";
import { etiquetaDeSubida, extensionesDeSubida, flujoDelArchivo } from "./logica";
import { TEXTOS } from "./textos";
import "./archivos.scss";

export interface PropsDeSubirArchivo {
  // El borrador de la obra (el de `ProveedorDeLaHoja`) y su `rev` vigente: lo importado entra en él.
  id: string;
  rev: number;
  // Dónde se pinta: fuera del contenido de la sección, que queda `inert` mientras el diálogo está abierto.
  anfitrion: HTMLElement;
  alCerrar: () => void;
  alAusente: () => void;
  // El servidor aceptó una fusión: su resumen es ahora el del borrador.
  alAceptar: (resumen: Resumen) => void;
  // Vuelve a leer el borrador del proveedor.
  alRecargar: () => Promise<void>;
  alReabrir: () => void;
  alExpirar: () => void;
  // El flujo de un .csv («Cargar cómputo», Tarea 12). Sin él la subida no acepta .csv.
  cuerpoDelComputo?: (archivo: File) => ReactNode;
}

// Por qué existe (Tarea 11 del plan F4): «Subir plano o cómputo» es la única puerta de Archivos y planos para lo que entra
// en el borrador desde un archivo. Una sola zona de soltar; el flujo lo elige la extensión: .dxf y .ifc van al plano
// (`ImportarPlano`, que antes vivía en la pestaña Espacio) y .csv al cómputo, que trae la Tarea 12. Es un diálogo propio
// (RNF-22), como los de las operaciones sobre versiones: foco adentro al abrirse, Tab atrapado y Esc o «Cerrar» lo cierran,
// salvo con una petición en vuelo (desde «Fusionar» hasta que se vuelve a leer el borrador), para no perder su resultado.
// Cerrarlo no descarta nada: la importación vive en el servidor y se ve al volver a abrirlo.
export function SubirArchivo({ id, rev, anfitrion, alCerrar, alAusente, alAceptar, alRecargar, alReabrir, alExpirar, cuerpoDelComputo }: PropsDeSubirArchivo) {
  const caja = useRef<HTMLDivElement>(null);
  const idTitulo = useId();
  const [archivo, setArchivo] = useState<File | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const cerrar = useCallback(() => {
    if (!ocupado) alCerrar();
  }, [alCerrar, ocupado]);
  const { atrapar } = useDialogo(caja, cerrar);
  const conComputo = cuerpoDelComputo !== undefined;
  const flujo = archivo === null ? null : flujoDelArchivo(archivo.name);

  return createPortal(
    <div className="silice-hoja__dialogo-fondo">
      <div
        ref={caja}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        tabIndex={-1}
        onKeyDown={atrapar}
        className="silice-hoja__dialogo silice-archivos__dialogo"
      >
        <h2 id={idTitulo} className="cds--type-heading-compact-02">
          {TEXTOS.subir}
        </h2>
        <SubidaArchivo etiqueta={etiquetaDeSubida({ plano: true, computo: conComputo })} extensiones={extensionesDeSubida({ plano: true, computo: conComputo })} alElegir={setArchivo} deshabilitada={ocupado} />
        {archivo !== null && <p className="cds--type-body-compact-01">Archivo elegido: {archivo.name}</p>}
        {flujo === "computo" && archivo !== null && cuerpoDelComputo ? (
          cuerpoDelComputo(archivo)
        ) : (
          <ImportarPlano
            id={id}
            rev={rev}
            archivo={flujo === "plano" ? archivo : null}
            alAusente={alAusente}
            alAceptar={alAceptar}
            alRecargar={alRecargar}
            alReabrir={alReabrir}
            alExpirar={alExpirar}
            alOcuparse={setOcupado}
          />
        )}
        <div className="silice-hoja__acciones">
          <Button kind="secondary" size="md" disabled={ocupado} onClick={cerrar}>
            {TEXTOS.cerrar}
          </Button>
        </div>
      </div>
    </div>,
    anfitrion,
  );
}
