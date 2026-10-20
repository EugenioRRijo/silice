import { Button } from "@carbon/react";
import { useEffect, useId, useRef } from "react";
import type { KeyboardEvent } from "react";

interface Props {
  titulo: string;
  texto: string;
  textoConfirmar: string;
  textoCancelar: string;
  alConfirmar: () => void;
  alCancelar: () => void;
}

// Confirmación que se comporta como diálogo: lleva el foco adentro, atrapa Tab, se cierra con Escape (en todo el documento) y el
// resto de la página queda `inert` mientras está abierta (lo decide quien la monta, que también devuelve el foco al cerrarla).
// No usa el Modal de Carbon: su archivo trae una URL de documentación que `npm run dist` rechaza (RNF-22), como en Administración.
export function DialogoDeVersion({ titulo, texto, textoConfirmar, textoCancelar, alConfirmar, alCancelar }: Props) {
  const caja = useRef<HTMLDivElement>(null);
  const idTitulo = useId();
  const idTexto = useId();
  useEffect(() => {
    caja.current?.focus();
    const alTeclear = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") alCancelar();
    };
    document.addEventListener("keydown", alTeclear);
    return () => document.removeEventListener("keydown", alTeclear);
  }, [alCancelar]);

  const atrapar = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key !== "Tab" || !caja.current) return;
    const botones = Array.from(caja.current.querySelectorAll<HTMLElement>("button:not([disabled])"));
    const primero = botones[0];
    const ultimo = botones[botones.length - 1];
    if (primero === undefined || ultimo === undefined) return;
    const activo = document.activeElement;
    if (e.shiftKey && (activo === primero || activo === caja.current)) {
      e.preventDefault();
      ultimo.focus();
    } else if (!e.shiftKey && activo === ultimo) {
      e.preventDefault();
      primero.focus();
    }
  };

  return (
    <div className="silice-hoja__dialogo-fondo">
      <div
        ref={caja}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        aria-describedby={idTexto}
        tabIndex={-1}
        onKeyDown={atrapar}
        className="silice-hoja__dialogo"
      >
        <h2 id={idTitulo} className="cds--type-heading-compact-02">
          {titulo}
        </h2>
        <p id={idTexto} className="cds--type-body-compact-01">
          {texto}
        </p>
        <div className="silice-hoja__acciones">
          <Button kind="danger" size="md" onClick={alConfirmar}>
            {textoConfirmar}
          </Button>
          <Button kind="secondary" size="md" onClick={alCancelar}>
            {textoCancelar}
          </Button>
        </div>
      </div>
    </div>
  );
}
