import { IconButton } from "@carbon/react";
import { Add, Reset, Subtract } from "@carbon/icons-react";
import { ZOOM_INICIAL, ZOOM_MAXIMO, ZOOM_MINIMO } from "./zoomHoja";

interface Props {
  // Zoom propio de la hoja, en porcentaje (50 a 300).
  zoom: number;
  // Razón que se le pidió a Univer (zoom propio × factor del tamaño de letra); 1 = 100 %.
  razon: number;
  // Univer recortó la razón a su tope.
  limitado: boolean;
  alBajar: () => void;
  alSubir: () => void;
  alRestablecer: () => void;
}

// Control de zoom de la barra de la hoja: − / valor / + / restablecer. El valor es una región viva educada
// (aria-live) para que el cambio se anuncie. En los topes el botón se marca con aria-disabled en vez de `disabled`:
// así el foco no se pierde al llegar al límite con el teclado.
export function ControlZoomHoja({ zoom, razon, limitado, alBajar, alSubir, alRestablecer }: Props) {
  const dibujado = Math.round(razon * 100);
  const distinto = dibujado !== zoom;
  return (
    <div role="group" aria-label="Zoom de la hoja" className="zoom-hoja">
      <IconButton
        label="Alejar la hoja"
        kind="ghost"
        size="sm"
        align="bottom"
        className="zoom-hoja__boton"
        aria-disabled={zoom <= ZOOM_MINIMO}
        onClick={() => zoom > ZOOM_MINIMO && alBajar()}
      >
        <Subtract />
      </IconButton>
      <output className="zoom-hoja__valor cds--type-body-compact-01" role="status" aria-live="polite" aria-atomic="true">
        {zoom} %
        {distinto && (
          <span className="silice-oculto">
            {`, la hoja se dibuja al ${dibujado} % por el tamaño de letra${limitado ? " (tope del lienzo)" : ""}`}
          </span>
        )}
      </output>
      <IconButton
        label="Acercar la hoja"
        kind="ghost"
        size="sm"
        align="bottom"
        className="zoom-hoja__boton"
        aria-disabled={zoom >= ZOOM_MAXIMO}
        onClick={() => zoom < ZOOM_MAXIMO && alSubir()}
      >
        <Add />
      </IconButton>
      <IconButton
        label="Restablecer el zoom de la hoja al 100 %"
        kind="ghost"
        size="sm"
        align="bottom-end"
        className="zoom-hoja__boton"
        aria-disabled={zoom === ZOOM_INICIAL}
        onClick={() => zoom !== ZOOM_INICIAL && alRestablecer()}
      >
        <Reset />
      </IconButton>
    </div>
  );
}
