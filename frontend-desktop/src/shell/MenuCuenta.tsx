import { ChevronDown, Logout, User } from "@carbon/icons-react";
import { useDespliegue } from "./useDespliegue";
import "./PanelCarpetaProyecto.scss";

interface Props {
  nombre: string;
  alSalir: () => void;
}

// La persona de la sesion y su menu: solo «Salir». Con letra grande o poco ancho el nombre se oculta por CSS y queda el
// icono; el nombre sigue en el nombre accesible. Comparte el SCSS del lado derecho de la barra.
export function MenuCuenta({ nombre, alSalir }: Props) {
  const { abierto, alternar, envoltorio, boton, alTeclear } = useDespliegue();
  return (
    <div className="silice-cuenta" ref={envoltorio} onKeyDown={alTeclear}>
      <button
        type="button"
        ref={boton}
        className="cds--header__action silice-cuenta__boton"
        aria-expanded={abierto}
        aria-controls="menu-cuenta"
        aria-label={`Cuenta de ${nombre}`}
        title={nombre}
        onClick={alternar}
      >
        <User size={16} aria-hidden="true" />
        <span className="silice-cuenta__nombre cds--type-body-compact-01">{nombre}</span>
        <ChevronDown size={16} aria-hidden="true" />
      </button>
      {abierto && (
        <div id="menu-cuenta" role="region" aria-label="Cuenta" className="silice-cuenta__panel">
          <button type="button" className="silice-cuenta__salir cds--type-body-compact-01" onClick={alSalir}>
            <Logout size={16} aria-hidden="true" />
            Salir
          </button>
        </div>
      )}
    </div>
  );
}
