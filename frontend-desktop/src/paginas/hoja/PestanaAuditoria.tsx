import { Button } from "@carbon/react";
import { useEffect, useRef } from "react";
import { InformeAuditoria } from "../../comun/InformeAuditoria";
import type { FiltroDeAuditoria } from "./ContextoAuditoria";
import { VistaCarga } from "./VistaCarga";
import { hallazgosDeOrigen, rutaDeVista } from "./logica";
import type { VistaAuditoria } from "./logica";

interface Props {
  id: string;
  alAusente: () => void;
  // Si se llegó desde el Estado de una fila, solo se ven los hallazgos que la nombran.
  filtro: FiltroDeAuditoria | null;
  alQuitarFiltro: () => void;
}

interface PropsContenido {
  informe: VistaAuditoria;
  filtro: FiltroDeAuditoria | null;
  alQuitarFiltro: () => void;
}

function ContenidoAuditoria({ informe, filtro, alQuitarFiltro }: PropsContenido) {
  const aviso = useRef<HTMLDivElement>(null);
  // Al llegar desde una fila el foco pasa al aviso del filtro: la fila que lo pidió ya no está en pantalla.
  useEffect(() => {
    if (filtro !== null) aviso.current?.focus();
  }, [filtro]);
  const propios = filtro === null ? informe.hallazgos : hallazgosDeOrigen(informe.hallazgos, filtro.claves);
  return (
    <div className="silice-hoja__pestana">
      <p className="cds--type-body-compact-01">
        El informe se genera siempre, con todas las reglas, sobre el borrador vigente.
      </p>
      {filtro !== null && (
        <div className="silice-hoja__filtro" ref={aviso} tabIndex={-1} role="status">
          <p className="cds--type-body-compact-01">Hallazgos de {filtro.rotulo}</p>
          <Button kind="tertiary" size="sm" onClick={alQuitarFiltro}>
            Quitar filtro
          </Button>
        </div>
      )}
      {filtro !== null && propios.length === 0 && (
        <p className="cds--type-body-compact-01">Ningún hallazgo del informe nombra a {filtro.rotulo}.</p>
      )}
      <InformeAuditoria informe={filtro === null ? informe : { ...informe, hallazgos: propios, sin_hallazgos: null }} />
    </div>
  );
}

// Pestaña «Auditoría»: el informe de todas las reglas sobre el borrador, con R17 (conexión de cada punto). Todo va como
// texto plano (el componente común lo garantiza).
export function PestanaAuditoria({ id, alAusente, filtro, alQuitarFiltro }: Props) {
  return (
    <VistaCarga<VistaAuditoria> ruta={rutaDeVista(id, "auditoria")} etiqueta="Auditoría" alAusente={alAusente}>
      {(informe) => <ContenidoAuditoria informe={informe} filtro={filtro} alQuitarFiltro={alQuitarFiltro} />}
    </VistaCarga>
  );
}
