import { WarningAltFilled } from "@carbon/icons-react";
import { Button } from "@carbon/react";
import { useCallback, useContext, useEffect, useId, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { createPortal } from "react-dom";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AreaTexto } from "../../comun/AreaTexto";
import { AvisoError } from "../../comun/AvisoError";
import { nombreDeResponsable } from "../../comun/responsable";
import { fechaEsVe } from "../../indicadores/formatoEsVe";
import { useAplicacion } from "../../shell/contexto";
import { useFormularioSucio } from "../../shell/sucio";
import { useAtraparFoco } from "../../shell/useAtraparFoco";
import { useFocoAlCerrar } from "./AgregarPartida";
import { ContextoDeDialogos } from "./ContextoDeDialogos";
import "./AprobacionDeVersion.scss";

// El estado de una versión en el ciclo de aprobación, como lo da `GET /v1/aprobaciones?proyecto=` (api/rutas/aprobaciones.py,
// Tarea 18): el último movimiento manda; `por` es el responsable «Nombre <login>» y `el`, la fecha y hora ISO.
interface EstadoDeVersion {
  estado: string;
  por: string | null;
  el: string | null;
  notas: string;
  armo: boolean;
}

const RUTA = "/v1/aprobaciones";
const LARGO_DE_NOTA = 2000;
const ID_NOTA = "hoja-aprobacion-nota";

const NOMBRES: Record<string, string> = {
  guardada: "Guardada",
  en_aprobacion: "En aprobación",
  retirada: "Retirada",
  aprobada: "Aprobada",
  aprobada_con_observaciones: "Aprobada con observaciones",
  devuelta: "Devuelta",
};
const APROBADAS = new Set(["aprobada", "aprobada_con_observaciones"]);
// Se puede enviar una versión guardada o retirada; la en aprobación, la aprobada y la devuelta no (Tarea 17).
const SE_ENVIAN = new Set(["guardada", "retirada"]);

// «Aprobada · Rita · 25/10/2026» (diseño de montar un presupuesto §5.4); «Guardada» y «En aprobación» sin más. Si quien dictaminó
// es quien la armó, se dice (la decisión de Eugenio: se permite y queda visible).
function textoDeEtiqueta(e: EstadoDeVersion): string {
  const nombre = NOMBRES[e.estado] ?? e.estado;
  if (e.estado === "guardada" || e.estado === "en_aprobacion" || e.por === null || e.el === null) return nombre;
  const partes = [nombre, nombreDeResponsable(e.por), fechaEsVe(e.el.slice(0, 10))];
  if (e.armo && APROBADAS.has(e.estado)) partes.push("aprobada por quien la armó");
  if (e.armo && e.estado === "devuelta") partes.push("devuelta por quien la armó");
  return partes.join(" · ");
}

// La respuesta trae `versiones` como objeto: si no (un servidor sin la ruta), no hay nada que decir.
function estadoDe(respuesta: unknown, version: string): EstadoDeVersion | null {
  const versiones = (respuesta as { versiones?: unknown } | null | undefined)?.versiones;
  if (typeof versiones !== "object" || versiones === null) return null;
  const estado = (versiones as Record<string, EstadoDeVersion | undefined>)[version];
  return estado && typeof estado.estado === "string" ? estado : null;
}

function textoDeEnvio(version: string, retirada: string | null): string {
  const enviado = `Se envió ${version} a aprobación.`;
  return retirada ? `${enviado} Se retiró ${retirada} de la aprobación.` : enviado;
}

type Lectura = { estado: "leyendo" } | { estado: "listo"; datos: EstadoDeVersion | null } | { estado: "fallo" };

interface Props {
  // La obra (su código en la sesión) y la versión guardada que tiene abierta la Hoja.
  proyecto: string;
  version: string;
  // Cambios sin guardar del borrador: no viajan con el envío y el diálogo lo dice.
  cambios: number;
  // «Hacer una versión nueva a partir de esta»: la Hoja va a «Presupuesto» con el borrador de esta versión (ya abierto).
  alHacerVersionNueva: () => void;
}

// Junto a la versión de la Hoja (Tarea 19; diseño §5.4): la etiqueta de su aprobación, «Enviar a aprobación…» y, si la
// devolvieron, sus notas y «Hacer una versión nueva a partir de esta». El estado se lee de la API al abrir la versión (también
// tras salir, entrar o reiniciar la API: lo guarda la carpeta) y otra vez tras enviar. Quien la monta le da una `key` por obra
// y versión: cambiar de versión empieza de cero. Si la lectura falla por el servidor se dice; un 403 o un 404 no dicen nada
// (la Hoja no depende de esto).
export function AprobacionDeVersion({ proyecto, version, cambios, alHacerVersionNueva }: Props) {
  const { alExpirar } = useAplicacion();
  const [intento, setIntento] = useState(0);
  const [lectura, setLectura] = useState<Lectura>({ estado: "leyendo" });
  const [aviso, setAviso] = useState("");
  const [enviando, setEnviando] = useState(false);
  const idZona = useId();
  const idBoton = `${idZona}-enviar`;
  const enfocarAlCerrar = useFocoAlCerrar();

  useEffect(() => {
    let vigente = true;
    pedir<unknown>(`${RUTA}?${new URLSearchParams({ proyecto }).toString()}`).then(
      (r) => {
        if (vigente) setLectura({ estado: "listo", datos: estadoDe(r, version) });
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        const delServidor = error instanceof ErrorDeApi && (error.estado === 0 || error.estado >= 500);
        setLectura(delServidor ? { estado: "fallo" } : { estado: "listo", datos: null });
      },
    );
    return () => {
      vigente = false;
    };
  }, [proyecto, version, intento, alExpirar]);

  const cerrar = useCallback(() => {
    setEnviando(false);
    enfocarAlCerrar(idBoton);
  }, [enfocarAlCerrar, idBoton]);

  const enviado = useCallback(
    (retirada: string | null) => {
      setEnviando(false);
      setAviso(textoDeEnvio(version, retirada));
      setIntento((n) => n + 1);
      enfocarAlCerrar(idZona);
    },
    [version, enfocarAlCerrar, idZona],
  );

  const hacerVersionNueva = () => {
    setAviso("Corrija y guarde: será una versión nueva.");
    alHacerVersionNueva();
  };

  const datos = lectura.estado === "listo" ? lectura.datos : null;
  if (lectura.estado === "leyendo" || (lectura.estado === "listo" && datos === null && aviso === "")) return null;

  return (
    <section id={idZona} tabIndex={-1} className="silice-hoja__aprobacion" aria-label="Aprobación de la versión">
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
          <div className="silice-hoja__acciones">
            {SE_ENVIAN.has(datos.estado) && (
              <Button id={idBoton} kind="tertiary" size="sm" onClick={() => setEnviando(true)}>
                Enviar a aprobación…
              </Button>
            )}
            {datos.estado === "devuelta" && (
              <Button kind="tertiary" size="sm" onClick={hacerVersionNueva}>
                Hacer una versión nueva a partir de esta
              </Button>
            )}
          </div>
        </>
      )}
      <p className="silice-hoja__aprobacion-aviso cds--type-body-compact-01" role="status">
        {aviso}
      </p>
      {enviando && (
        <DialogoEnviar proyecto={proyecto} version={version} cambios={cambios} alEnviado={enviado} alCancelar={cerrar} />
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
