import { useRef } from "react";
import type { JSX, KeyboardEvent } from "react";
import { PanelLateral } from "../../comun/PanelLateral";
import { enfocables, useAtraparFoco } from "../../shell/useAtraparFoco";
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
//
// Foco (WCAG 2.4.3): el panel va en la capa modal del diálogo, con un velo a pantalla completa, y `PanelLateral` no atrapa
// el foco (las Tareas 6 y 7 lo usan sin velo). Aquí se atrapa con un contenedor `display: contents` (no cambia la
// maquetación): Tab y Mayús+Tab circulan solo dentro del panel. Mayús+Tab desde el título (el foco inicial, que no está
// en el orden de tabulación) también da la vuelta. Los eventos del diálogo «Precios distintos…» (otro sitio del DOM) llegan
// aquí por el árbol de React, pero su foco no es ni el primero ni el último del panel, así que no los toca.
//
// Capa (pasada de navegador del cierre de F4, H1): el panel va «en-capa», siempre por encima del velo, fijo bajo la barra
// superior, opaco y con su propio desplazamiento, con cualquier letra. Antes eso lo daba una regla de hijo directo del
// fondo que nunca aplicaba por este envoltorio, y con letra Normal el panel salía transparente y de 2190 px de alto.
export function ComponerEnPanel({ codigo, alCerrar, alGuardar }: Props): JSX.Element | null {
  const contenedor = useRef<HTMLDivElement>(null);
  const atrapar = useAtraparFoco(contenedor);
  const alTeclear = (e: KeyboardEvent<HTMLDivElement>) => {
    const caja = contenedor.current;
    const activo = document.activeElement;
    if (
      e.key === "Tab" &&
      e.shiftKey &&
      caja &&
      activo instanceof HTMLElement &&
      activo.tagName === "H2" &&
      caja.contains(activo)
    ) {
      e.preventDefault();
      enfocables(caja).at(-1)?.focus();
      return;
    }
    atrapar(e);
  };
  return (
    <div ref={contenedor} style={{ display: "contents" }} onKeyDown={alTeclear}>
      <PanelLateral titulo="Componer una partida" abierto={codigo !== null} alCerrar={alCerrar} ancho="ancho" modo="en-capa">
        <p role="note" className="silice-hoja__aviso-catalogo cds--type-body-compact-01">
          {AVISO_DEL_CATALOGO}
        </p>
        {codigo !== null && <ComponerPartida codigoInicial={codigo} nivelDelTitulo={2} alGuardar={alGuardar} />}
      </PanelLateral>
    </div>
  );
}
