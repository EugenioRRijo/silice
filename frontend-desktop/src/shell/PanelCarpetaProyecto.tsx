import { Folder } from "@carbon/icons-react";
import { useId } from "react";
import type { ReactNode } from "react";
import type { CasosRespuesta, ProyectoRespuesta } from "../api/tipos";
import { SelectorCaso, SelectorProyecto, nombreDeCarpeta, rotuloDeProyecto } from "./Selectores";
import { useDespliegue } from "./useDespliegue";
import "./PanelCarpetaProyecto.scss";

interface Props {
  casos: CasosRespuesta | null;
  proyectos: ProyectoRespuesta[] | null;
  // Codigo del proyecto elegido, o null.
  elegido: string | null;
  puedeCambiar: boolean;
  ocupado: boolean;
  alElegirCaso: (nombre: string) => void;
  alElegirProyecto: (codigo: string | null) => void;
  // Hueco al final del panel (carpetas de trabajo, proyecto nuevo).
  children?: ReactNode;
}

export { nombreDeCarpeta };

// «Carpeta y proyecto» siempre a la vista, a la derecha de la barra. El texto se recorta por CSS (puntos suspensivos); el
// nombre completo va en el nombre accesible. Con letra grande o poco ancho solo queda el icono (el nombre accesible no cambia).
export function PanelCarpetaProyecto({
  casos,
  proyectos,
  elegido,
  puedeCambiar,
  ocupado,
  alElegirCaso,
  alElegirProyecto,
  children,
}: Props) {
  const idPanel = useId();
  const { abierto, alternar, envoltorio, boton, alTeclear } = useDespliegue();
  const carpeta = casos ? nombreDeCarpeta(casos.actual.nombre) : "Sin carpeta";
  const actual = proyectos?.find((p) => p.codigo === elegido);
  const proyecto = actual && proyectos ? rotuloDeProyecto(actual, proyectos) : "Sin proyecto";
  return (
    <div className="silice-contexto" ref={envoltorio} onKeyDown={alTeclear}>
      <button
        type="button"
        ref={boton}
        className="cds--header__action silice-contexto__boton"
        aria-expanded={abierto}
        aria-controls={idPanel}
        aria-label={`Carpeta de trabajo: ${carpeta}. Proyecto: ${proyecto}. Cambiar`}
        title={`${carpeta} · ${proyecto}`}
        onClick={alternar}
      >
        <Folder size={16} aria-hidden="true" />
        <span className="silice-contexto__texto cds--type-body-compact-01">{`${carpeta} · ${proyecto}`}</span>
      </button>
      {abierto && (
        <div id={idPanel} role="region" aria-label="Carpeta y proyecto" className="silice-contexto__panel">
          <p className="silice-contexto__titulo cds--type-label-01">Carpeta y proyecto</p>
          {casos && (
            <SelectorCaso casos={casos} puedeCambiar={puedeCambiar} ocupado={ocupado} alElegir={alElegirCaso} />
          )}
          {proyectos && <SelectorProyecto proyectos={proyectos} elegido={elegido} alElegir={alElegirProyecto} />}
          {children}
        </div>
      )}
    </div>
  );
}
