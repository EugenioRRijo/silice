import { Button } from "@carbon/react";
import { Close } from "@carbon/icons-react";
import { useEffect, useId, useRef } from "react";
import type { JSX, KeyboardEvent, ReactNode } from "react";
import "./PanelLateral.scss";

export interface PropsDelPanelLateral {
  titulo: string;
  abierto: boolean;
  alCerrar: () => void;
  // «normal» mide 24 rem; «ancho», 40 rem (el APU de una partida, con sus tablas por rubro).
  ancho?: "normal" | "ancho";
  children: ReactNode;
}

// Por qué existe (plan F4, Tareas 6 y 7): el inventario pide un panel acoplado a la derecha en las cuatro secciones de la
// obra: el APU de una partida (Tarea 7, el primero que lo usa), el registro de cambios de una versión (Tarea 6), Componer
// (Tarea 9) y el informe de importación (Tarea 11). No es un diálogo (RNF-22: los diálogos son los propios del proyecto):
// es una región que se queda junto al contenido, como la columna del recorrido, y no atrapa el foco. Quien lo usa lo pone
// en un contenedor `silice-con-panel` (el contenido a la izquierda, el panel a la derecha); por debajo del umbral de la letra
// pasa por encima del contenido. Al abrirse el foco va a su h2; Esc o «Cerrar» lo cierran y el foco vuelve al control que
// lo abrió (el último, si se abrió otra vez con otro título). Sin animación.
export function PanelLateral({ titulo, abierto, alCerrar, ancho = "normal", children }: PropsDelPanelLateral): JSX.Element | null {
  const idTitulo = useId();
  const panel = useRef<HTMLElement>(null);
  const encabezado = useRef<HTMLHeadingElement>(null);
  const disparador = useRef<HTMLElement | null>(null);

  // Al abrirse, o al cambiar de título (otra fila lo abrió), se recuerda quién tenía el foco y el foco pasa al h2. Si el
  // foco ya estaba dentro del panel, el disparador sigue siendo el de antes.
  useEffect(() => {
    if (!abierto) return;
    const activo = document.activeElement;
    if (activo instanceof HTMLElement && !panel.current?.contains(activo)) disparador.current = activo;
    encabezado.current?.focus();
  }, [abierto, titulo]);

  // Al cerrarse (o al desmontarse abierto) el foco vuelve al disparador, si sigue en la página.
  useEffect(() => {
    if (!abierto) return;
    return () => {
      const anterior = disparador.current;
      disparador.current = null;
      if (anterior?.isConnected) anterior.focus();
    };
  }, [abierto]);

  if (!abierto) return null;

  // Esc cierra solo si nació dentro del panel (en el DOM: un diálogo abierto desde aquí se pinta en otro sitio) y si ningún
  // control de dentro lo usó ya (un campo de celda lo usa para volver a su valor).
  const alTeclear = (e: KeyboardEvent<HTMLElement>) => {
    if (e.key !== "Escape" || e.defaultPrevented || !e.currentTarget.contains(e.target as Node)) return;
    e.preventDefault();
    alCerrar();
  };

  return (
    <aside
      ref={panel}
      aria-labelledby={idTitulo}
      className={ancho === "ancho" ? "silice-panel-lateral silice-panel-lateral--ancho" : "silice-panel-lateral"}
      onKeyDown={alTeclear}
    >
      <div className="silice-panel-lateral__cabecera">
        <h2 id={idTitulo} ref={encabezado} tabIndex={-1} className="silice-panel-lateral__titulo cds--type-heading-compact-02">
          {titulo}
        </h2>
        <Button kind="ghost" size="sm" renderIcon={Close} onClick={alCerrar}>
          Cerrar
        </Button>
      </div>
      {children}
    </aside>
  );
}
