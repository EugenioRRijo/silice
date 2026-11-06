import { WarningAltFilled } from "@carbon/icons-react";
import { Button } from "@carbon/react";
import { useContext, useEffect, useId, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { createPortal } from "react-dom";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { ESTADOS_APROBADOS, nombreDeEstado } from "../../comun/aprobacion";
import type { EstadoDeAprobacion } from "../../comun/aprobacion";
import { AreaTexto } from "../../comun/AreaTexto";
import { AvisoError } from "../../comun/AvisoError";
import { nombreDeResponsable } from "../../comun/responsable";
import { fechaEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { useFormularioSucio } from "../../shell/sucio";
import { useAtraparFoco } from "../../shell/useAtraparFoco";
import { ContextoDeDialogos } from "./ContextoDeDialogos";
import type { LecturaDeAprobacion } from "./useAprobacionDeVersion";
import "./AprobacionDeVersion.scss";

const RUTA = "/v1/aprobaciones";
const LARGO_DE_NOTA = 2000;
const ID_NOTA = "hoja-aprobacion-nota";

// «Aprobada · Rita · 25/10/2026» (diseño de montar un presupuesto §5.4); «Guardada» y «En aprobación» sin más. Si quien dictaminó
// es quien la armó, se dice (la decisión de Eugenio: se permite y queda visible).
function textoDeEtiqueta(e: EstadoDeAprobacion): string {
  const nombre = nombreDeEstado(e.estado);
  if (e.estado === "guardada" || e.estado === "en_aprobacion" || e.por === null || e.el === null) return nombre;
  const partes = [nombre, nombreDeResponsable(e.por), fechaEsVe(e.el.slice(0, 10))];
  if (e.armo && ESTADOS_APROBADOS.has(e.estado)) partes.push("aprobada por quien la armó");
  if (e.armo && e.estado === "devuelta") partes.push("devuelta por quien la armó");
  return partes.join(" · ");
}

interface Props {
  // El id de la región: a ella vuelve el foco tras enviar.
  id: string;
  // La obra (su código en la sesión) y la versión guardada que tiene abierta la Hoja.
  proyecto: string;
  version: string;
  // Cambios sin guardar del borrador: no viajan con el envío y el diálogo lo dice.
  cambios: number;
  // La lectura de `useAprobacionDeVersion`, que es de quien monta esto (la franja también la usa).
  lectura: LecturaDeAprobacion;
  // Lo último que pasó («Se envió…», «Corrija y guarde…»): se lee en un `status`.
  aviso: string;
  // El diálogo de enviar está abierto (lo abre «Enviar a aprobación…» de la franja).
  enviando: boolean;
  alEnviado: (retirada: string | null) => void;
  alCancelarEnvio: () => void;
}

// Junto a la versión de la Hoja (Tarea 19; diseño §5.4): la etiqueta de su aprobación, sus notas si las hay y el diálogo de
// enviar. Desde la cabecera compacta (2026-11-05) va dentro de la línea de estado y su fila corre en línea con la versión y
// el total; las notas y el aviso bajan a una fila propia solo cuando hay algo que decir. Desde la Tarea 5 del plan F4 los botones («Enviar a aprobación…», «Hacer una versión nueva») son de la franja del
// paso, que es el único botón principal de la pantalla, y la lectura del estado vive en `useAprobacionDeVersion`. Si la
// lectura falla se dice; mientras se lee, o sin nada que decir, no se pinta nada (la Hoja no depende de esto).
export function AprobacionDeVersion({ id, proyecto, version, cambios, lectura, aviso, enviando, alEnviado, alCancelarEnvio }: Props) {
  const datos = lectura.estado === "listo" ? lectura.datos : null;
  // Sin registro de la versión la franja ofrece enviar igual (regla 8): el diálogo tiene que poder abrirse.
  if (lectura.estado === "leyendo" || (lectura.estado === "listo" && datos === null && aviso === "" && !enviando)) return null;

  return (
    <section id={id} tabIndex={-1} className="silice-hoja__aprobacion" aria-label="Aprobación de la versión">
      {lectura.estado === "fallo" && (
        <p className="cds--type-helper-text-01">No se pudo leer el estado de aprobación de esta versión.</p>
      )}
      {datos !== null && (
        <>
          <p className="silice-hoja__aprobacion-fila cds--type-body-compact-01">
            <span className="silice-hoja__aprobacion-rotulo">Aprobación:</span>
            <span className="silice-hoja__aprobacion-etiqueta" data-estado={datos.estado}>
              {datos.estado === "devuelta" && (
                <WarningAltFilled size={16} className="silice-hoja__aprobacion-icono" aria-hidden="true" />
              )}
              {textoDeEtiqueta(datos)}
            </span>
          </p>
          {datos.notas.trim() !== "" && datos.por !== null && (
            <p className="silice-hoja__aprobacion-notas cds--type-body-compact-01">
              Notas de {nombreDeResponsable(datos.por)}: {datos.notas}
            </p>
          )}
          {datos.estado === "en_aprobacion" && (
            <p className="cds--type-helper-text-01">La versión enviada no se edita: si guarda cambios, será una versión nueva.</p>
          )}
        </>
      )}
      <p className="silice-hoja__aprobacion-aviso silice-hoja__region-viva cds--type-body-compact-01" role="status">
        {aviso}
      </p>
      {enviando && (
        <DialogoEnviar proyecto={proyecto} version={version} cambios={cambios} alEnviado={alEnviado} alCancelar={alCancelarEnvio} />
      )}
    </section>
  );
}

interface PropsDialogo {
  proyecto: string;
  version: string;
  cambios: number;
  alEnviado: (retirada: string | null) => void;
  alCancelar: () => void;
}

function textoDeCambios(cambios: number): string | null {
  if (cambios === 0) return null;
  if (cambios === 1) return "El cambio sin guardar no se envía: guárdelo antes si debe revisarse.";
  return `Los ${cambios} cambios sin guardar no se envían: guárdelos antes si deben revisarse.`;
}

// «Enviar a aprobación» (diseño §5.4): la versión tal como se guardó y una nota opcional (`POST /v1/aprobaciones`). Diálogo
// propio, como los demás de la Hoja: se pinta fuera del contenido (que queda `inert`), foco en la nota, Tab atrapado, Esc
// cierra y, mientras va la petición, no se cierra (no se pierde la respuesta). Un rechazo (ya en aprobación, devuelta, cadena
// rota) se dice con el texto del servidor y el diálogo sigue abierto.
function DialogoEnviar({ proyecto, version, cambios, alEnviado, alCancelar }: PropsDialogo) {
  const { alExpirar } = useAplicacion();
  const { anfitrion, registrar } = useContext(ContextoDeDialogos);
  const caja = useRef<HTMLDivElement>(null);
  const atrapar = useAtraparFoco(caja);
  const idTitulo = useId();
  const idTexto = useId();
  const idFormulario = useId();
  const [nota, setNota] = useState("");
  const [mandando, setMandando] = useState(false);
  const [error, setError] = useState<unknown>(null);

  // La nota escrita cuenta como trabajo sin guardar mientras el diálogo está abierto.
  useFormularioSucio("hoja", nota.trim() !== "");

  useEffect(() => {
    registrar(1);
    return () => registrar(-1);
  }, [registrar]);

  useEffect(() => {
    if (anfitrion !== null) document.getElementById(ID_NOTA)?.focus();
  }, [anfitrion]);

  const cancelar = () => {
    if (!mandando) alCancelar();
  };

  const alTeclear = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Escape") {
      e.preventDefault();
      cancelar();
      return;
    }
    atrapar(e);
  };

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (mandando) return;
    setMandando(true);
    setError(null);
    try {
      const r = await pedir<{ retirada?: string | null }>(RUTA, { metodo: "POST", cuerpo: { proyecto, version, nota } });
      alEnviado(r?.retirada ?? null);
    } catch (e) {
      setMandando(false);
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      else setError(e);
    }
  }

  if (anfitrion === null) return null;
  const sinGuardar = textoDeCambios(cambios);
  return createPortal(
    <div className="silice-hoja__dialogo-fondo">
      <div
        ref={caja}
        role="dialog"
        aria-modal="true"
        aria-labelledby={idTitulo}
        aria-describedby={idTexto}
        tabIndex={-1}
        onKeyDown={alTeclear}
        className="silice-hoja__dialogo silice-hoja__dialogo--operacion"
      >
        <h2 id={idTitulo} className="cds--type-heading-compact-02">
          Enviar a aprobación
        </h2>
        <div id={idTexto}>
          <p className="cds--type-body-compact-01">Quien revisa verá la versión {version} tal como se guardó y dará su dictamen.</p>
          {sinGuardar && <p className="cds--type-body-compact-01">{sinGuardar}</p>}
        </div>
        <form id={idFormulario} className="silice-hoja__campos-operacion" noValidate onSubmit={(e) => void enviar(e)}>
          <AreaTexto
            id={ID_NOTA}
            labelText="Nota para quien revisa (opcional)"
            rows={3}
            maxLength={LARGO_DE_NOTA}
            value={nota}
            disabled={mandando}
            onChange={(e) => setNota(e.target.value)}
          />
        </form>
        <p className="cds--type-helper-text-01" aria-live="polite">
          {mandando ? "Enviando la versión a aprobación…" : ""}
        </p>
        <AvisoError error={error} titulo="No se envió la versión" />
        <div className="silice-hoja__acciones">
          <Button kind="secondary" size="md" disabled={mandando} onClick={cancelar}>
            Cancelar
          </Button>
          <Button kind="primary" size="md" type="submit" form={idFormulario} disabled={mandando}>
            Enviar a aprobación
          </Button>
        </div>
      </div>
    </div>,
    anfitrion,
  );
}
