import { Button, InlineNotification } from "@carbon/react";
import type { ReactNode } from "react";
import { useCallback, useId, useRef } from "react";
import { createPortal } from "react-dom";
import { TITULO_DE_ERROR } from "./logicaVersiones";
import type { ErrorDeOperacion, Operacion } from "./logicaVersiones";
import { useDialogo } from "./useDialogo";

interface Props {
  operacion: Operacion;
  titulo: string;
  descripcion?: ReactNode;
  // Dónde se pinta (fuera del resto de la página, que queda `inert`).
  anfitrion: HTMLElement;
  // «Nombre <login>»: el responsable es la persona de la sesión, de solo lectura (RF-82).
  usuario: string;
  // Por qué todavía no se puede enviar, o null.
  motivo: string | null;
  textoConfirmar: string;
  enviando: boolean;
  error: ErrorDeOperacion | null;
  alConfirmar: () => void;
  alCancelar: () => void;
  // Los campos del formulario.
  children: ReactNode;
}

const CONTROLES = "select, input, textarea";

// El diálogo de una operación sobre versiones. Se comporta como `DialogoDeGuardar`: foco al primer campo, Tab atrapado, Esc
// cierra; mientras la petición está en vuelo no se cierra (ni Esc ni Cancelar) para no perder el error del servidor, que se
// muestra tal cual y deja el formulario como estaba.
export function DialogoDeOperacion(p: Props) {
  const caja = useRef<HTMLDivElement>(null);
  const idTitulo = useId();
  const idDescripcion = useId();
  const idMotivo = useId();
  const { alCancelar, enviando } = p;
  const cancelar = useCallback(() => {
    if (!enviando) alCancelar();
  }, [alCancelar, enviando]);
  const { atrapar } = useDialogo(caja, cancelar, () => caja.current?.querySelector<HTMLElement>(CONTROLES) ?? null);
  const e = p.error;

  return createPortal(
    <div className="silice-hoja__dialogo-fondo">
      <div
        ref={caja}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        aria-describedby={p.descripcion !== undefined ? idDescripcion : undefined}
        tabIndex={-1}
        onKeyDown={atrapar}
        className="silice-hoja__dialogo silice-hoja__dialogo--operacion"
      >
        <h2 id={idTitulo} className="cds--type-heading-compact-02">
          {p.titulo}
        </h2>
        {p.descripcion !== undefined && (
          <p id={idDescripcion} className="cds--type-body-compact-01">
            {p.descripcion}
          </p>
        )}
        <div className="silice-hoja__campos-operacion">{p.children}</div>
        {p.motivo !== null && (
          <p id={idMotivo} className="cds--type-helper-text-01">
            {p.motivo}
          </p>
        )}
        <p className="cds--type-body-compact-01">Responsable: {p.usuario}</p>
        <p className="cds--type-helper-text-01" aria-live="polite">
          {p.enviando ? "Guardando la versión…" : ""}
        </p>
        {e !== null && (
          <InlineNotification
            kind="error"
            role="alert"
            lowContrast
            hideCloseButton
            title={TITULO_DE_ERROR[p.operacion]}
            subtitle={e.mensaje}
          />
        )}
        <div className="silice-hoja__acciones">
          <Button kind="secondary" size="md" disabled={p.enviando} onClick={cancelar}>
            Cancelar
          </Button>
          <Button
            kind="primary"
            size="md"
            disabled={p.motivo !== null || p.enviando}
            aria-describedby={p.motivo !== null ? idMotivo : undefined}
            onClick={p.alConfirmar}
          >
            {p.textoConfirmar}
          </Button>
        </div>
      </div>
    </div>,
    p.anfitrion,
  );
}
