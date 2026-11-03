import type { JSX } from "react";
import { PanelLateral } from "../../comun/PanelLateral";
import { ComponerPartida } from "../componer/ComponerPartida";
import type { PartidaCompuesta } from "../componer/ComponerPartida";

const AVISO_DEL_CATALOGO = "Esto cambia el catálogo de la empresa: la partida queda para todas las obras.";

interface Props {
  // El código con que se pidió componer, o null con el panel cerrado.
  codigo: string | null;
  alCerrar: () => void;
  alGuardar: (partida: PartidaCompuesta) => void;
}

// Por qué existe (plan F4, Tarea 9, baja 21): «Componer una partida nueva» ya no sale de la obra; se abre en el panel
// ancho, junto al diálogo «Agregar partida», que espera oculto y queda con la partida guardada elegida. El aviso del
// catálogo va siempre a la vista: lo que se guarda aquí sirve a todas las obras. Solo lo usa ese diálogo; la composición
// es la misma de la pantalla `componer` (`ComponerPartida`).
export function ComponerEnPanel({ codigo, alCerrar, alGuardar }: Props): JSX.Element | null {
  return (
    <PanelLateral titulo="Componer una partida" abierto={codigo !== null} alCerrar={alCerrar} ancho="ancho">
      <p role="note" className="silice-hoja__aviso-catalogo cds--type-body-compact-01">
        {AVISO_DEL_CATALOGO}
      </p>
      {codigo !== null && <ComponerPartida codigoInicial={codigo} nivelDelTitulo={2} alGuardar={alGuardar} />}
    </PanelLateral>
  );
}
