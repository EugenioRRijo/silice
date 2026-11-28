import { Notification } from "@carbon/icons-react";
import type { JSX } from "react";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { useNotificaciones } from "./ProveedorDeNotificaciones";
import "./Campanita.scss";

export interface PropsDeCampanita {
  sinLeer?: number;
  abierto?: boolean;
  idPanel?: string;
  alAlternar?: () => void;
}

export function Campanita({
  sinLeer: sinLeerProp,
  abierto: abiertoProp,
  idPanel: idPanelProp,
  alAlternar,
}: PropsDeCampanita = {}): JSX.Element {
  // Por separado: el registro de la campanita va a `ref` y el resto se lee al pintar (react-hooks/refs).
  const { registrarCampanita, sinLeer: sinLeerDelContexto, panelAbierto, idPanel: idDelContexto, alternarPanel } = useNotificaciones();
  const sinLeer = sinLeerProp ?? sinLeerDelContexto;
  const abierto = abiertoProp ?? panelAbierto;
  const idPanel = idPanelProp ?? idDelContexto;
  const alternar = alAlternar ?? alternarPanel;
  const cifraTexto = formatoEsVe(String(sinLeer));
  const etiqueta = sinLeer > 0 ? `Notificaciones, ${cifraTexto} sin leer` : "Notificaciones";

  return (
    <button
      ref={registrarCampanita}
      type="button"
      className="silice-campanita"
      aria-label={etiqueta}
      aria-expanded={abierto}
      aria-controls={idPanel}
      onClick={alternar}
    >
      <Notification size={16} aria-hidden="true" />
      {sinLeer > 0 && (
        <span className="silice-campanita__cuenta" aria-hidden="true">
          {cifraTexto}
        </span>
      )}
    </button>
  );
}
