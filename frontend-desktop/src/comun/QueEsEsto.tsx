import { Button } from "@carbon/react";
import { Help } from "@carbon/icons-react";
import { useId } from "react";
import type { JSX, ReactNode } from "react";
import { useDespliegue } from "../shell/useDespliegue";
import "./QueEsEsto.scss";

interface Props {
  // El nombre de la región que se abre: el título de la pantalla o la pestaña que explica.
  titulo: string;
  children: ReactNode;
}

// Por qué existe (Tarea 4 del plan F4, baja 25): el texto largo que iba encima de cada pestaña estorbaba a quien ya sabe
// usarla y no se perdía para quien no. Queda plegado tras «¿Qué es esto?». Lo usan las siete pestañas del Presupuesto
// (`paginas/hoja/AyudaDePestana.tsx`) y F6 lo convertirá en el panel de ayuda de toda la obra. Se abre con clic o teclado
// (Esc lo cierra y devuelve el foco al botón: `useDespliegue`); el panel se queda en la página, no flota, así que empuja el
// contenido en vez de tapar la tabla. Plegado no está en el DOM: sus enlaces no entran en el orden de tabulación.
export function QueEsEsto({ titulo, children }: Props): JSX.Element {
  const idPanel = useId();
  const { abierto, alternar, envoltorio, boton, alTeclear } = useDespliegue();
  return (
    <div className="silice-que-es-esto" ref={envoltorio} onKeyDown={alTeclear}>
      <Button
        ref={boton}
        kind="ghost"
        size="sm"
        renderIcon={Help}
        aria-expanded={abierto}
        aria-controls={abierto ? idPanel : undefined}
        onClick={alternar}
      >
        ¿Qué es esto?
      </Button>
      {abierto && (
        <div id={idPanel} role="region" aria-label={titulo} className="silice-que-es-esto__panel cds--type-body-compact-01">
          {children}
        </div>
      )}
    </div>
  );
}
