import { useEffect, useId, useRef } from "react";
import type { JSX, KeyboardEvent, ReactNode } from "react";
import { ID_BOTON_OBRA } from "../SelectorObra";
import { useAtraparFoco } from "../useAtraparFoco";
import "./MarcoDeDialogo.scss";

interface Props {
  titulo: string;
  alCerrar: () => void;
  // El cuerpo del dialogo y su pie (los botones, a lo ancho, como el pie de un modal de Carbon).
  children: ReactNode;
  pie: ReactNode;
  // Lo que recibe el foco al abrir (por omision, la propia caja, que lee el titulo).
  inicial?: () => HTMLElement | null;
  ancho?: "normal" | "ancho";
}

// Dialogo propio del armazon (carpetas de trabajo, «Nueva obra»), como «Cambios sin guardar»: sin el Modal de Carbon (su
// archivo trae una URL de documentacion que `npm run dist` rechaza, RNF-22), modal, Tab atrapado (`useAtraparFoco`), Esc
// cierra y, al desmontarse, el foco vuelve a quien lo tenia al abrir (el boton de la obra de la barra) o, si ya no esta,
// a ese boton. Va por debajo de «Cambios sin guardar», que puede abrirse encima.
export function MarcoDeDialogo({ titulo, alCerrar, children, pie, inicial, ancho = "normal" }: Props): JSX.Element {
  const base = useId();
  const caja = useRef<HTMLDivElement>(null);
  const atrapar = useAtraparFoco(caja);

  useEffect(() => {
    const previo = document.activeElement;
    (inicial?.() ?? caja.current)?.focus();
    return () => {
      const destino = previo instanceof HTMLElement && previo.isConnected ? previo : document.getElementById(ID_BOTON_OBRA);
      destino?.focus();
    };
    // Solo al abrir y al cerrar: un dialogo no le quita el foco a quien escribe cuando cambia su contenido.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function alTeclear(e: KeyboardEvent<HTMLDivElement>) {
    if (e.key === "Escape") {
      // Esc es de este dialogo: ni el sidebar ni el panel de detras se enteran.
      e.preventDefault();
      e.stopPropagation();
      alCerrar();
      return;
    }
    atrapar(e);
  }

  return (
    <div className="silice-dialogo__fondo">
      <div
        ref={caja}
        role="dialog"
        aria-modal="true"
        aria-labelledby={`${base}-titulo`}
        tabIndex={-1}
        className={`silice-dialogo${ancho === "ancho" ? " silice-dialogo--ancho" : ""}`}
        onKeyDown={alTeclear}
      >
        <h2 id={`${base}-titulo`} className="silice-dialogo__titulo cds--type-heading-compact-02">
          {titulo}
        </h2>
        <div className="silice-dialogo__cuerpo">{children}</div>
        <div className="silice-dialogo__pie">{pie}</div>
      </div>
    </div>
  );
}
