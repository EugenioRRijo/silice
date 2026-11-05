import { Button } from "@carbon/react";
import { ChevronDown, Education } from "@carbon/icons-react";
import { useId } from "react";
import type { JSX } from "react";
import { useDespliegue } from "./useDespliegue";
import "./MarcaDemostracion.scss";

interface Props {
  // La carpeta de esta sesion es la de demostracion (`es_demostracion` de `GET /v1/casos`).
  activa: boolean;
  // La cuenta puede abrir otra carpeta (`abrir_carpeta`).
  puedeVolver: boolean;
  alVolver: () => void;
}

// En la carpeta de demostracion la barra lo dice siempre, en los tres modulos (diseno de modulos §7 y §12.2): texto e
// icono, no solo color. Abre un panel con lo que significa y, para quien puede cambiar de carpeta, «Volver a la carpeta
// de la empresa».
export function MarcaDemostracion({ activa, puedeVolver, alVolver }: Props): JSX.Element | null {
  const idPanel = useId();
  const { abierto, alternar, envoltorio, boton, alTeclear } = useDespliegue();
  if (!activa) return null;
  return (
    <div className="silice-demo" ref={envoltorio} onKeyDown={alTeclear}>
      <button
        type="button"
        ref={boton}
        className="cds--header__action silice-demo__boton"
        aria-expanded={abierto}
        aria-controls={idPanel}
        aria-label="Demostración: está viendo datos inventados"
        onClick={alternar}
      >
        <Education size={16} aria-hidden="true" />
        <span className="cds--type-body-compact-01">Demostración</span>
        <ChevronDown size={16} aria-hidden="true" />
      </button>
      {abierto && (
        <div id={idPanel} role="region" aria-label="Demostración" className="silice-demo__panel">
          <p className="cds--type-body-compact-01">Está viendo datos inventados.</p>
          <p className="silice-demo__ayuda cds--type-helper-text-01">
            Sirven para aprender a usar Sílice; no son una obra real.
          </p>
          {puedeVolver && (
            <Button
              kind="tertiary"
              size="sm"
              onClick={() => {
                alternar();
                boton.current?.focus();
                alVolver();
              }}
            >
              Volver a la carpeta de la empresa
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
