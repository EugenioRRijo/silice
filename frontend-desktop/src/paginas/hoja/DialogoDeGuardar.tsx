import {
  Button,
  InlineNotification,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@carbon/react";
import { useId, useRef } from "react";
import { CampoTexto } from "../../comun/CampoTexto";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { rotuloDeOrigen } from "./logica";
import type { Monto } from "./logica";
import { FUENTE_DEL_CAMBIO, FUENTE_DE_LA_MEDIDA, motivoParaNoGuardar, textoDeCambiosAGuardar } from "./logicaGuardar";
import type { ErrorDeGuardado } from "./logicaGuardar";
import type { CambiosDelModal } from "./useGuardado";
import { useDialogo } from "./useDialogo";

// Cuántos cambios se pintan a la vez en el modal (una hoja grande puede tener miles): el resto se dice, no se oculta.
export const CAMBIOS_VISIBLES = 200;
// El tope de la fuente en el contrato de S1.
export const LARGO_DE_FUENTE = 300;

const TITULO_DE_ERROR: Record<ErrorDeGuardado["clase"], string> = {
  "mas-nueva": "Hay una versión más nueva",
  rev: "El borrador cambió",
  "ya-guardado": "Este borrador ya se guardó",
  ausente: "El borrador ya no está",
  permiso: "Sin permiso para guardar",
  rechazo: "No se guardó nada",
  base: "No se guardó nada",
  otro: "No se guardó nada",
};

interface Props {
  proyecto: string;
  // La versión abierta, o null: es la primera versión del proyecto.
  version: string | null;
  soloLectura: boolean;
  cambiosSinGuardar: number;
  total: Monto;
  moneda: string;
  // «Nombre <login>»: el responsable es la persona de la sesión, de solo lectura (RF-82).
  usuario: string;
  fuente: string;
  alCambiarFuente: (texto: string) => void;
  cambios: CambiosDelModal;
  enviando: boolean;
  error: ErrorDeGuardado | null;
  alGuardar: (confirmarVersionMasNueva: boolean) => void;
  alCancelar: () => void;
  // Lo que se ofrece según el fallo.
  alRecargar: () => void;
  alAbrirVersion: (version: string) => void;
  alAbrirDeNuevo: () => void;
}

function ListaDeCambios({ cambios, primera }: { cambios: CambiosDelModal; primera: boolean }) {
  const titulo = useId();
  if (cambios === null) return <p className="cds--type-helper-text-01" aria-live="polite">Leyendo los cambios…</p>;
  if (cambios === "error") return <p className="cds--type-helper-text-01" role="status">No se pudo leer la lista de cambios.</p>;
  if (cambios.length === 0) {
    return primera ? null : <p className="cds--type-helper-text-01">No hay cambios que mostrar.</p>;
  }
  const visibles = cambios.slice(0, CAMBIOS_VISIBLES);
  return (
    <section aria-labelledby={titulo} className="silice-hoja__cambios-guardar">
      <h3 id={titulo} className="cds--type-heading-compact-01">
        Cambios ({cambios.length})
      </h3>
      <div className="silice-hoja__cambios" role="region" aria-label="Lista de cambios: desplazar" tabIndex={0}>
        <Table size="sm" aria-label="Cambios que se guardan">
          <TableHead>
            <TableRow>
              {["Objeto", "Clave", "Campo", "Antes", "Después"].map((c) => (
                <TableHeader key={c} scope="col">
                  {c}
                </TableHeader>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {visibles.map((c, i) => (
              <TableRow key={i}>
                <TableCell>{c.objeto}</TableCell>
                <TableCell title={c.clave}>{rotuloDeOrigen(c.clave)}</TableCell>
                <TableCell>{c.campo}</TableCell>
                <TableCell>{c.antes}</TableCell>
                <TableCell>{c.despues}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      {cambios.length > visibles.length && (
        <p className="cds--type-helper-text-01">
          Se muestran los primeros {visibles.length} de {cambios.length} cambios; se guardan todos.
        </p>
      )}
    </section>
  );
}

// El modal «Guardar versión» (y «Guardar primera versión»): la fuente, el responsable de la sesión, el resumen y la lista de
// cambios. Se comporta como `DialogoDeVersion` (foco adentro, Tab atrapado, Esc, el resto `inert` lo decide quien lo monta).
export function DialogoDeGuardar(p: Props) {
  const caja = useRef<HTMLDivElement>(null);
  const idTitulo = useId();
  const idResumen = useId();
  const idMotivo = useId();
  const idFuente = useId();
  const { atrapar } = useDialogo(caja, p.alCancelar, () => document.getElementById(idFuente));
  const primera = p.version === null;
  const titulo = primera ? "Guardar primera versión" : "Guardar versión";
  const motivo = motivoParaNoGuardar({ fuente: p.fuente, primera, cambios: p.cambiosSinGuardar, soloLectura: p.soloLectura });
  // Con un fallo que pide decidir (versión más nueva, ya guardado, borrador ausente) no hay nada que reintentar tal cual.
  const sinReintento = p.error?.clase === "mas-nueva" || p.error?.clase === "ya-guardado" || p.error?.clase === "ausente";
  const e = p.error;

  return (
    <div className="silice-hoja__dialogo-fondo">
      <div
        ref={caja}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        aria-describedby={idResumen}
        tabIndex={-1}
        onKeyDown={atrapar}
        className="silice-hoja__dialogo silice-hoja__dialogo--guardar"
      >
        <h2 id={idTitulo} className="cds--type-heading-compact-02">
          {titulo}
        </h2>
        <p id={idResumen} className="cds--type-body-compact-01">
          {primera
            ? `Es la primera versión del proyecto ${p.proyecto}: registra su creación con la fuente y el responsable.`
            : `Se registrarán ${textoDeCambiosAGuardar(p.cambiosSinGuardar)} en una versión nueva (sale de la ${p.version}).`}
        </p>
        <p className="cds--type-body-compact-01">
          Total{" "}
          <span title={p.total.exacto}>
            {formatoEsVe(p.total.texto)} {p.moneda}
          </span>
          <span className="cds--visually-hidden"> Valor exacto {p.total.exacto}</span>
        </p>
        <CampoTexto
          id={idFuente}
          labelText={primera ? FUENTE_DE_LA_MEDIDA : FUENTE_DEL_CAMBIO}
          value={p.fuente}
          maxLength={LARGO_DE_FUENTE}
          onChange={(ev) => p.alCambiarFuente(ev.target.value)}
          aria-describedby={motivo !== null ? idMotivo : undefined}
        />
        {motivo !== null && (
          <p id={idMotivo} className="cds--type-helper-text-01">
            {motivo}
          </p>
        )}
        <p className="cds--type-body-compact-01">Responsable: {p.usuario}</p>
        <ListaDeCambios cambios={p.cambios} primera={primera} />
        <p className="cds--type-helper-text-01" aria-live="polite">
          {p.enviando ? "Guardando la versión…" : ""}
        </p>
        {e !== null && (
          <div className="silice-hoja__aviso-edicion">
            <InlineNotification
              kind={e.clase === "mas-nueva" || e.clase === "rev" || e.clase === "ausente" ? "warning" : "error"}
              role="alert"
              lowContrast
              hideCloseButton
              title={TITULO_DE_ERROR[e.clase]}
              subtitle={e.mensaje}
            />
            <div className="silice-hoja__acciones">
              {e.clase === "mas-nueva" && (
                <Button kind="danger--tertiary" size="sm" disabled={p.enviando} onClick={() => p.alGuardar(true)}>
                  Guardar de todos modos
                </Button>
              )}
              {(e.clase === "mas-nueva" || e.clase === "ya-guardado") && e.version !== null && (
                <Button kind="tertiary" size="sm" disabled={p.enviando} onClick={() => p.alAbrirVersion(e.version!)}>
                  Abrir la versión {e.version}
                </Button>
              )}
              {e.clase === "rev" && (
                <Button kind="tertiary" size="sm" disabled={p.enviando} onClick={p.alRecargar}>
                  Recargar el borrador
                </Button>
              )}
              {e.clase === "ausente" && (
                <Button kind="tertiary" size="sm" disabled={p.enviando} onClick={p.alAbrirDeNuevo}>
                  Abrir de nuevo
                </Button>
              )}
            </div>
          </div>
        )}
        <div className="silice-hoja__acciones">
          <Button kind="secondary" size="md" onClick={p.alCancelar}>
            Cancelar
          </Button>
          <Button
            kind="primary"
            size="md"
            disabled={motivo !== null || p.enviando || sinReintento}
            aria-describedby={motivo !== null ? idMotivo : undefined}
            onClick={() => p.alGuardar(false)}
          >
            {titulo}
          </Button>
        </div>
      </div>
    </div>
  );
}
