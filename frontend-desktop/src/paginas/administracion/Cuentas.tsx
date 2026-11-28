import { WarningAltFilled } from "@carbon/icons-react";
import { Button, Checkbox, Select, SelectItem } from "@carbon/react";
import { InlineNotification, PasswordInput } from "../../comun/carbonEs";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import type { FormEvent, KeyboardEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { CampoTexto } from "../../comun/CampoTexto";
import { Dialogo } from "../../comun/Dialogo";
import { TablaDensa } from "../../comun/TablaDensa";
import type { FilaDensa } from "../../comun/TablaDensa";
import { mensajeDeError } from "../../comun/errores";
import { fechaEsVe } from "../../indicadores/formatoEsVe";
import { rutaDeActividad } from "../../marco/espacios";
import { useAplicacion } from "../../shell/contexto";
import {
  AVISO_TEMPORAL,
  AYUDA_CONTRASENA,
  AYUDA_DESBLOQUEAR,
  AYUDA_USUARIO,
  errorDeUsuario,
  CONFIRMACIONES,
  ROLES,
  avisoDeRoles,
  errorDeContrasena,
  etiquetaDeRol,
  filasDeCuentas,
  contrasenaValida,
  puedeCrear,
} from "./logica";
import type { Cuenta, CuentasRespuesta, ResultadoCuenta } from "./logica";

type Resultado =
  | { tipo: "ok"; mensaje: string; aviso: string | null; nota: string | null }
  | { tipo: "error"; error: unknown };

type Pendiente = { tipo: "desactivar" | "restablecer"; id: number; login: string; propia: boolean };

type PapelDeSolicitud = "arma" | "revisa";

interface SolicitudDeCuenta {
  id: number;
  nombre: string;
  login: string;
  correo: string;
  creada: string;
  estado: string;
  papel: string | null;
  vence: string | null;
}

interface SolicitudesRespuesta {
  solicitudes: SolicitudDeCuenta[];
}

interface AprobacionRespuesta {
  codigo: string;
  vence: string;
  mailto: string;
}

interface MensajeRespuesta {
  mensaje: string;
}

interface CodigoMostrado {
  nombre: string;
  login: string;
  codigo: string;
  vence: string;
  mailto: string;
}

const AVISO_SIN_ROL = "Sin ningún rol la cuenta no podría hacer nada: marque al menos uno para crearla.";

const ESTADOS_DE_SOLICITUD: Record<string, string> = {
  pendiente: "Pendiente",
  aprobada: "Aprobada",
  rechazada: "Rechazada",
  usada: "Usada",
  vencida: "Vencida",
};

function fechaSolicitudEsVe(iso: string): string {
  const m = /^(\d{4}-\d{2}-\d{2})/.exec(iso.trim());
  return m ? fechaEsVe(m[1]!) : iso;
}

function vencimientoEsVe(iso: string): string {
  return fechaEsVe(iso.trim().replace(" ", "T"));
}

function filasDeSolicitudes(solicitudes: readonly SolicitudDeCuenta[]): FilaDensa[] {
  return solicitudes.map((s) => ({
    id: String(s.id),
    nombre: s.nombre,
    usuario: s.login,
    correo: s.correo,
    fecha: fechaSolicitudEsVe(s.creada),
    estado: ESTADOS_DE_SOLICITUD[s.estado] ?? s.estado,
    accion: "",
  }));
}

function SelectorDeRoles({
  idBase,
  leyenda,
  elegidos,
  alCambiar,
  deshabilitado = false,
  descritoPor,
}: {
  idBase: string;
  leyenda: string;
  elegidos: string[];
  alCambiar: (roles: string[]) => void;
  deshabilitado?: boolean;
  descritoPor?: string;
}) {
  return (
    <fieldset className="cds--fieldset" disabled={deshabilitado} aria-describedby={descritoPor}>
      <legend className="cds--label">{leyenda}</legend>
      {ROLES.map((rol) => (
        <Checkbox
          key={rol}
          id={`${idBase}-${rol}`}
          labelText={etiquetaDeRol(rol)}
          checked={elegidos.includes(rol)}
          disabled={deshabilitado}
          onChange={(_, { checked }) => alCambiar(checked ? [...elegidos, rol] : elegidos.filter((r) => r !== rol))}
        />
      ))}
    </fieldset>
  );
}

// Confirmacion que se comporta como dialogo: lleva el foco adentro, atrapa Tab, se cierra con Escape (en todo el
// documento) y el resto de la pagina queda `inert` mientras esta abierta (lo decide quien la monta). No usa el Modal
// de Carbon: su archivo trae una URL de documentacion que `npm run dist` rechaza (RNF-22). El texto se fija al abrir:
// no cambia si se toca otra cosa. Quien la monta devuelve el foco al abrirla (o al aviso del resultado).
function Confirmacion({
  pendiente,
  alConfirmar,
  alCancelar,
}: {
  pendiente: Pendiente;
  alConfirmar: () => void;
  alCancelar: () => void;
}) {
  const caja = useRef<HTMLDivElement>(null);
  const textos = CONFIRMACIONES[pendiente.tipo];
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
    if (botones.length === 0) return;
    const primero = botones[0];
    const ultimo = botones[botones.length - 1];
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
    <div
      ref={caja}
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="adm-confirmar-titulo"
      aria-describedby="adm-confirmar-texto"
      tabIndex={-1}
      onKeyDown={atrapar}
      className={`silice-adm__confirmar${pendiente.tipo === "desactivar" ? " silice-adm__confirmar--peligro" : ""}`}
    >
      <h3 id="adm-confirmar-titulo" className="cds--type-heading-compact-01">
        {textos.titulo}
      </h3>
      <p id="adm-confirmar-texto" className="cds--type-body-compact-01">
        {textos.texto(pendiente.login)}
        {pendiente.propia && ` ${textos.propia}`}
      </p>
      <div className="silice-adm__acciones">
        <Button
          kind={pendiente.tipo === "desactivar" ? "danger" : "primary"}
          size="md"
          aria-label={`${textos.boton} ${pendiente.tipo === "desactivar" ? "a" : "la contraseña de"} ${pendiente.login}`}
          onClick={alConfirmar}
        >
          {textos.boton}
        </Button>
        <Button kind="secondary" size="md" onClick={alCancelar}>
          Cancelar
        </Button>
      </div>
    </div>
  );
}

// Pestana «Cuentas» (accion ADMINISTRAR_CUENTAS): solicitudes con código de un solo uso (C9), lista, alta, roles,
// desactivar/reactivar, desbloquear y restablecer la contrasena. Las contrasenas y códigos viven solo en el estado de
// este componente y se vacian al enviar o al cerrar el diálogo; la API nunca los guarda en claro.
export default function Cuentas() {
  const { alExpirar, sesion } = useAplicacion();
  const [lista, setLista] = useState<CuentasRespuesta | null>(null);
  const [solicitudes, setSolicitudes] = useState<SolicitudDeCuenta[]>([]);
  const [papelesElegidos, setPapelesElegidos] = useState<Record<number, PapelDeSolicitud>>({});
  const [aprobada, setAprobada] = useState<CodigoMostrado | null>(null);
  const [estadoCopia, setEstadoCopia] = useState<"ok" | "error" | null>(null);
  const [solicitudARechazar, setSolicitudARechazar] = useState<SolicitudDeCuenta | null>(null);
  const [errorDeLista, setErrorDeLista] = useState<unknown>(null);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const aviso = useRef<HTMLDivElement>(null);
  const montado = useRef(true);
  const quienAbrio = useRef<HTMLElement | null>(null);
  const selectorDeCuenta = useRef<HTMLSelectElement>(null);

  const [login, setLogin] = useState("");
  const [nombre, setNombre] = useState("");
  const [rolesNuevos, setRolesNuevos] = useState<string[]>([]);
  const [rolesTocados, setRolesTocados] = useState(false);
  const [temporal, setTemporal] = useState("");

  const [elegidaId, setElegidaId] = useState<number | null>(null);
  const [nueva, setNueva] = useState("");
  const [pendiente, setPendiente] = useState<Pendiente | null>(null);

  const cuentas = lista?.cuentas ?? [];
  const elegida: Cuenta | undefined = cuentas.find((c) => c.id === elegidaId);
  const solicitudPorId = new Map(solicitudes.map((s) => [String(s.id), s]));

  useEffect(() => {
    montado.current = true;
    return () => {
      montado.current = false;
    };
  }, []);

  // Recarga la lista. Si falla, se conserva la que ya habia y se avisa con «Reintentar». Devuelve si salio bien.
  const cargar = useCallback(async (): Promise<boolean> => {
    try {
      const r = await pedir<CuentasRespuesta>("/v1/cuentas");
      if (!montado.current) return true;
      setLista(r);
      setErrorDeLista(null);
      return true;
    } catch (e) {
      if (!montado.current) return false;
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setErrorDeLista(e);
      return false;
    }
  }, [alExpirar]);

  const cargarSolicitudes = useCallback(async (): Promise<boolean> => {
    try {
      const r = await pedir<SolicitudesRespuesta>("/v1/solicitudes");
      if (!montado.current) return true;
      setSolicitudes(r.solicitudes);
      return true;
    } catch (e) {
      if (!montado.current) return false;
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      return false;
    }
  }, [alExpirar]);

  useEffect(() => {
    let vigente = true;
    pedir<CuentasRespuesta>("/v1/cuentas").then(
      (r) => {
        if (vigente) setLista(r);
      },
      (e: unknown) => {
        if (!vigente) return;
        if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
        setErrorDeLista(e);
      },
    );
    pedir<SolicitudesRespuesta>("/v1/solicitudes").then(
      (r) => {
        if (vigente) setSolicitudes(r.solicitudes);
      },
      (e: unknown) => {
        if (!vigente) return;
        if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      },
    );
    return () => {
      vigente = false;
    };
  }, [alExpirar]);

  // Los roles editados vuelven a los de la cuenta al cambiar de cuenta o al recargar la lista.
  const clave = `${elegida?.id ?? ""}:${elegida?.roles.join(",") ?? ""}`;
  const [edicion, setEdicion] = useState<{ clave: string; roles: string[] }>({ clave, roles: elegida?.roles ?? [] });
  if (edicion.clave !== clave) setEdicion({ clave, roles: elegida?.roles ?? [] });
  const rolesEditados = edicion.roles;

  // El foco anuncia el resultado de cada accion.
  useEffect(() => {
    if (resultado) aviso.current?.focus();
  }, [resultado]);

  // Al cancelar la confirmacion el foco vuelve al control que la abrio (al confirmar, va al resultado).
  useEffect(() => {
    if (pendiente === null && quienAbrio.current) {
      const previo = quienAbrio.current;
      quienAbrio.current = null;
      if (previo.isConnected) previo.focus();
    }
  }, [pendiente]);

  const papelDe = (s: SolicitudDeCuenta): PapelDeSolicitud =>
    papelesElegidos[s.id] ?? (s.papel === "revisa" ? "revisa" : "arma");

  const aprobarSolicitud = async (s: SolicitudDeCuenta) => {
    setOcupado(true);
    setResultado(null);
    try {
      const r = await pedir<AprobacionRespuesta>(`/v1/solicitudes/${s.id}/aprobar`, {
        metodo: "POST",
        cuerpo: { papel: papelDe(s) },
      });
      if (!montado.current) return;
      await cargarSolicitudes();
      if (!montado.current) return;
      setEstadoCopia(null);
      setAprobada({
        nombre: s.nombre,
        login: s.login,
        codigo: r.codigo,
        vence: r.vence,
        mailto: r.mailto,
      });
    } catch (e) {
      if (!montado.current) return;
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setResultado({ tipo: "error", error: e });
    } finally {
      if (montado.current) setOcupado(false);
    }
  };

  const cerrarDialogoCodigo = useCallback(() => {
    setAprobada(null);
    setEstadoCopia(null);
  }, []);

  const copiarCodigo = async () => {
    if (!aprobada) return;
    try {
      if (!navigator.clipboard?.writeText) throw new Error("Sin portapapeles");
      await navigator.clipboard.writeText(aprobada.codigo);
      if (montado.current) setEstadoCopia("ok");
    } catch {
      if (montado.current) setEstadoCopia("error");
    }
  };

  const cerrarRechazo = useCallback(() => {
    setSolicitudARechazar(null);
  }, []);

  const confirmarRechazo = async () => {
    if (!solicitudARechazar) return;
    const objetivo = solicitudARechazar;
    setOcupado(true);
    setResultado(null);
    try {
      const r = await pedir<MensajeRespuesta>(`/v1/solicitudes/${objetivo.id}/rechazar`, {
        metodo: "POST",
        cuerpo: {},
      });
      if (!montado.current) return;
      setSolicitudARechazar(null);
      const recargo = await cargarSolicitudes();
      if (!montado.current) return;
      setResultado({
        tipo: "ok",
        mensaje: r.mensaje,
        aviso: null,
        nota: recargo ? null : "La solicitud se rechazó, pero no se pudo recargar la lista de solicitudes.",
      });
    } catch (e) {
      if (!montado.current) return;
      setSolicitudARechazar(null);
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setResultado({ tipo: "error", error: e });
    } finally {
      if (montado.current) setOcupado(false);
    }
  };

  // Manda una accion; devuelve true si la API la acepto. Recarga la lista despues.
  const ejecutar = async (ruta: string, cuerpo: object): Promise<boolean> => {
    setOcupado(true);
    setResultado(null);
    try {
      const r = await pedir<ResultadoCuenta>(ruta, { metodo: "POST", cuerpo });
      if (!montado.current) return true;
      const recargo = await cargar();
      if (!montado.current) return true;
      setResultado({
        tipo: "ok",
        mensaje: r.mensaje,
        aviso: r.aviso,
        nota: recargo ? null : "La acción se hizo, pero no se pudo recargar la lista de cuentas. Use «Reintentar».",
      });
      return true;
    } catch (e) {
      if (!montado.current) return false;
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setResultado({ tipo: "error", error: e });
      return false;
    } finally {
      if (montado.current) setOcupado(false);
    }
  };

  const crear = async (evento: FormEvent) => {
    evento.preventDefault();
    if (!puedeCrear(login, nombre, temporal, rolesNuevos)) return;
    const cuerpo = { login, nombre, roles: rolesNuevos, contrasena_temporal: temporal };
    setTemporal(""); // se vacia al enviar, haya exito o no
    if (await ejecutar("/v1/cuentas", cuerpo) && montado.current) {
      setLogin("");
      setNombre("");
      setRolesNuevos([]);
      setRolesTocados(false);
    }
  };

  const abrirConfirmacion = (tipo: Pendiente["tipo"]) => {
    if (!elegida) return;
    quienAbrio.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    setPendiente({ tipo, id: elegida.id, login: elegida.login, propia: elegida.login === sesion.login });
  };

  const cancelar = useCallback(() => {
    setNueva(""); // cancelar tambien vacia la contrasena escrita
    setPendiente(null);
  }, []);

  const confirmar = async () => {
    if (!pendiente) return;
    const { tipo, id } = pendiente;
    quienAbrio.current = null; // el foco va al resultado, no al boton
    setPendiente(null);
    if (tipo === "restablecer") {
      const cuerpo = { contrasena_temporal: nueva };
      setNueva("");
      await ejecutar(`/v1/cuentas/${id}/restablecer`, cuerpo);
    } else {
      await ejecutar(`/v1/cuentas/${id}/desactivar`, {});
    }
  };

  const abierta = pendiente !== null;
  const avisoEnEdicion = lista ? avisoDeRoles(rolesEditados, lista.aviso_arma_y_revisa) : null;
  const avisoEnAlta = lista ? avisoDeRoles(rolesNuevos, lista.aviso_arma_y_revisa) : null;
  const sinElegir = elegida === undefined;
  const de = (verbo: string) => (elegida ? `${verbo} ${elegida.login}` : undefined);

  return (
    <div className="silice-adm__secciones">
      {solicitudes.length > 0 && (
        <section aria-labelledby="adm-solicitudes" className="silice-adm__tabla" inert={abierta}>
          <h2 id="adm-solicitudes" className="cds--type-heading-compact-02">
            Solicitudes
          </h2>
          <TablaDensa
            etiqueta="Solicitudes de cuenta"
            columnas={[
              { clave: "nombre", titulo: "Nombre" },
              { clave: "usuario", titulo: "Usuario" },
              { clave: "correo", titulo: "Correo" },
              { clave: "fecha", titulo: "Fecha" },
              { clave: "estado", titulo: "Estado" },
              {
                clave: "accion",
                titulo: "Acción",
                ordenable: false,
                celda: (f) => {
                  const s = solicitudPorId.get(f.id);
                  // Las mismas que el servidor puede resolver (`RESOLUBLES` en seguridad/solicitudes.py): una aprobada también, para
                  // volver a aprobarla con un código nuevo (el anterior deja de valer) o rechazarla.
                  if (!s || (s.estado !== "pendiente" && s.estado !== "vencida" && s.estado !== "aprobada")) return "—";
                  const idQuien = `adm-sol-quien-${s.id}`;
                  return (
                    <div className="silice-adm__acciones-solicitud">
                      <span id={idQuien} className="cds--visually-hidden">
                        {`${s.nombre} (${s.login})`}
                      </span>
                      <div className="silice-adm__selector-papel">
                        <Select
                          id={`adm-sol-papel-${s.id}`}
                          labelText="Papel"
                          hideLabel
                          size="sm"
                          aria-describedby={idQuien}
                          value={papelDe(s)}
                          disabled={ocupado}
                          onChange={(e) => {
                            const valor: PapelDeSolicitud = e.target.value === "revisa" ? "revisa" : "arma";
                            setPapelesElegidos((prev) => ({ ...prev, [s.id]: valor }));
                          }}
                        >
                          <SelectItem value="arma" text="Arma presupuestos" />
                          <SelectItem value="revisa" text="Revisa" />
                        </Select>
                      </div>
                      <Button
                        kind="secondary"
                        size="sm"
                        type="button"
                        disabled={ocupado}
                        aria-describedby={idQuien}
                        onClick={() => void aprobarSolicitud(s)}
                      >
                        Aprobar y generar el código
                      </Button>
                      <Button
                        kind="danger--tertiary"
                        size="sm"
                        type="button"
                        disabled={ocupado}
                        aria-describedby={idQuien}
                        onClick={() => setSolicitudARechazar(s)}
                      >
                        Rechazar
                      </Button>
                    </div>
                  );
                },
              },
            ]}
            filas={filasDeSolicitudes(solicitudes)}
          />
        </section>
      )}

      <section aria-labelledby="adm-cuentas" className="silice-adm__tabla" inert={abierta}>
        <h2 id="adm-cuentas" className="cds--type-heading-compact-02">
          Cuentas
        </h2>
        {errorDeLista !== null && (
          <div className="silice-adm__reintento">
            <InlineNotification
              kind="error"
              title="No se pudieron leer las cuentas"
              subtitle={mensajeDeError(errorDeLista)}
              lowContrast
              hideCloseButton
            />
            <Button kind="tertiary" size="md" onClick={() => void cargar()}>
              Reintentar
            </Button>
          </div>
        )}
        {(errorDeLista === null || lista !== null) && (
          <TablaDensa
            etiqueta="Cuentas de la instalación"
            cargando={lista === null}
            columnas={[
              { clave: "usuario", titulo: "Usuario" },
              { clave: "nombre", titulo: "Nombre" },
              { clave: "roles", titulo: "Roles" },
              { clave: "activa", titulo: "Activa" },
              {
                clave: "accion",
                titulo: "Acción",
                ordenable: false,
                // Cada fila dice de qué cuenta es (WCAG 2.4.6) y elige por su id; el foco pasa al selector de abajo.
                celda: (f) => (
                  <div className="silice-adm__acciones">
                    <Button
                      kind="ghost"
                      size="sm"
                      aria-label={`Elegir la cuenta ${String(f.usuario)}`}
                      onClick={() => {
                        setElegidaId(Number(f.id));
                        selectorDeCuenta.current?.focus();
                      }}
                    >
                      Elegir
                    </Button>
                    <Link to={rutaDeActividad(String(f.usuario))} aria-label={`Ver su actividad: ${String(f.usuario)}`} className="cds--link">
                      Ver su actividad
                    </Link>
                  </div>
                ),
              },
            ]}
            filas={filasDeCuentas(cuentas)}
            vacio={{ titulo: "Todavía no hay cuentas" }}
          />
        )}
      </section>

      <div ref={aviso} tabIndex={-1} role="group" aria-label="Resultado de la última acción" className="silice-adm__resultado">
        {resultado?.tipo === "ok" && (
          <>
            <InlineNotification kind="success" title="Hecho" subtitle={resultado.mensaje} lowContrast hideCloseButton />
            {resultado.aviso && (
              <InlineNotification kind="warning" title="Aviso" subtitle={resultado.aviso} lowContrast hideCloseButton />
            )}
            {resultado.nota && (
              <InlineNotification kind="warning" title="Lista sin actualizar" subtitle={resultado.nota} lowContrast hideCloseButton />
            )}
          </>
        )}
        {resultado?.tipo === "error" && (
          <InlineNotification
            kind="error"
            title="No se pudo completar la acción"
            subtitle={mensajeDeError(resultado.error)}
            lowContrast
            hideCloseButton
          />
        )}
      </div>

      <section aria-labelledby="adm-crear" className="silice-adm__seccion" inert={abierta}>
        <h2 id="adm-crear" className="cds--type-heading-compact-02">
          Crear una cuenta
        </h2>
        <form className="silice-adm__seccion" onSubmit={(e) => void crear(e)} autoComplete="off">
          <CampoTexto
            id="adm-login"
            labelText="Usuario"
            helperText={AYUDA_USUARIO}
            required
            invalid={errorDeUsuario(login) !== null}
            invalidText={errorDeUsuario(login) ?? ""}
            value={login}
            onChange={(e) => setLogin(e.target.value)}
          />
          <CampoTexto id="adm-nombre" labelText="Nombre de la persona" required value={nombre} onChange={(e) => setNombre(e.target.value)} />
          <SelectorDeRoles
            idBase="adm-roles"
            leyenda="Qué puede hacer"
            elegidos={rolesNuevos}
            alCambiar={(roles) => {
              setRolesNuevos(roles);
              setRolesTocados(true);
            }}
            descritoPor="adm-roles-pista"
          />
          {/* La pista es neutra y describe el grupo y el boton. La region de estado queda siempre montada para que el
              lector de pantalla anuncie el aviso al aparecer: sale tras tocar el grupo o con el resto del alta listo,
              que es cuando explica por que el boton no deja crear. */}
          <div className="silice-adm__nota cds--type-label-01">
            <p id="adm-roles-pista">Marque al menos un rol.</p>
            <p role="status">
              {rolesNuevos.length === 0 && (rolesTocados || puedeCrear(login, nombre, temporal)) && (
                <span className="silice-sev silice-sev--advertencia">
                  <WarningAltFilled size={16} className="silice-sev__icono" aria-hidden="true" />
                  {AVISO_SIN_ROL}
                </span>
              )}
            </p>
          </div>
          {avisoEnAlta && <p className="silice-adm__nota cds--type-label-01">{avisoEnAlta}</p>}
          <PasswordInput
            id="adm-temporal"
            autoComplete="new-password"
            labelText="Contraseña temporal"
            helperText={`${AYUDA_CONTRASENA} ${AVISO_TEMPORAL}`}
            showPasswordLabel="Mostrar contraseña"
            hidePasswordLabel="Ocultar contraseña"
            invalid={errorDeContrasena(temporal) !== null}
            invalidText={errorDeContrasena(temporal) ?? ""}
            required
            value={temporal}
            onChange={(e) => setTemporal(e.target.value)}
          />
          <div>
            <Button
              type="submit"
              kind="primary"
              size="md"
              aria-describedby="adm-roles-pista"
              disabled={ocupado || !puedeCrear(login, nombre, temporal, rolesNuevos)}
            >
              Crear la cuenta
            </Button>
          </div>
        </form>
      </section>

      {cuentas.length > 0 && (
        <section aria-labelledby="adm-cambiar" className="silice-adm__seccion">
          <h2 id="adm-cambiar" className="cds--type-heading-compact-02">
            {elegida ? `Cambiar la cuenta ${elegida.login}` : "Cambiar una cuenta"}
          </h2>
          <div className="silice-adm__seccion" inert={abierta}>
            <Select
              ref={selectorDeCuenta}
              id="adm-cuenta"
              labelText="Cuenta que va a cambiar"
              value={elegida ? String(elegida.id) : ""}
              onChange={(e) => setElegidaId(e.target.value === "" ? null : Number(e.target.value))}
            >
              <SelectItem value="" text="Elija una cuenta" hidden />
              {cuentas.map((c) => (
                <SelectItem key={c.id} value={String(c.id)} text={c.login} />
              ))}
            </Select>
            <SelectorDeRoles
              idBase="adm-roles-de"
              leyenda="Qué puede hacer la cuenta"
              elegidos={rolesEditados}
              alCambiar={(roles) => setEdicion({ clave, roles })}
              deshabilitado={sinElegir}
            />
            {avisoEnEdicion && <p className="silice-adm__nota cds--type-label-01">{avisoEnEdicion}</p>}
            <div className="silice-adm__acciones">
              <Button
                kind="secondary"
                size="md"
                disabled={ocupado || sinElegir}
                aria-label={de("Guardar roles de")}
                onClick={() => elegida && void ejecutar(`/v1/cuentas/${elegida.id}/roles`, { roles: rolesEditados })}
              >
                Guardar roles
              </Button>
              {elegida?.activa === false ? (
                <Button
                  kind="secondary"
                  size="md"
                  disabled={ocupado}
                  aria-label={de("Reactivar a")}
                  onClick={() => void ejecutar(`/v1/cuentas/${elegida.id}/reactivar`, {})}
                >
                  Reactivar
                </Button>
              ) : (
                <Button
                  kind="danger--tertiary"
                  size="md"
                  disabled={ocupado || sinElegir}
                  aria-label={de("Desactivar a")}
                  onClick={() => abrirConfirmacion("desactivar")}
                >
                  Desactivar
                </Button>
              )}
              <Button
                kind="secondary"
                size="md"
                disabled={ocupado || sinElegir}
                aria-label={de("Desbloquear a")}
                aria-describedby="adm-ayuda-desbloquear"
                onClick={() => elegida && void ejecutar(`/v1/cuentas/${elegida.id}/desbloquear`, {})}
              >
                Desbloquear
              </Button>
            </div>
            <p id="adm-ayuda-desbloquear" className="silice-adm__nota cds--type-label-01">
              Desbloquear: {AYUDA_DESBLOQUEAR.charAt(0).toLowerCase() + AYUDA_DESBLOQUEAR.slice(1)}
            </p>
          </div>
          <form
            className="silice-adm__seccion"
            autoComplete="off"
            inert={abierta}
            onSubmit={(e) => {
              e.preventDefault();
              if (contrasenaValida(nueva)) abrirConfirmacion("restablecer");
            }}
          >
            <PasswordInput
              id="adm-restablecer"
              autoComplete="new-password"
              labelText="Contraseña temporal nueva"
              helperText={AYUDA_CONTRASENA}
              showPasswordLabel="Mostrar contraseña"
              hidePasswordLabel="Ocultar contraseña"
              invalid={errorDeContrasena(nueva) !== null}
              invalidText={errorDeContrasena(nueva) ?? ""}
              disabled={sinElegir}
              value={nueva}
              onChange={(e) => setNueva(e.target.value)}
            />
            <div>
              <Button
                type="submit"
                kind="tertiary"
                size="md"
                disabled={ocupado || sinElegir || !contrasenaValida(nueva)}
                aria-label={de("Restablecer la contraseña de")}
              >
                Restablecer la contraseña
              </Button>
            </div>
          </form>
          {pendiente && <Confirmacion pendiente={pendiente} alConfirmar={() => void confirmar()} alCancelar={cancelar} />}
        </section>
      )}

      <Dialogo
        abierto={solicitudARechazar !== null}
        titulo="Rechazar la solicitud"
        alCerrar={cerrarRechazo}
        enviando={ocupado}
        destructivo
        pie={[
          <Button key="cancelar" kind="secondary" size="md" type="button" disabled={ocupado} onClick={cerrarRechazo}>
            Cancelar
          </Button>,
          <Button
            key="rechazar"
            kind="danger"
            size="md"
            type="button"
            disabled={ocupado}
            onClick={() => void confirmarRechazo()}
          >
            Rechazar la solicitud
          </Button>,
        ]}
      >
        {solicitudARechazar && (
          <p className="cds--type-body-compact-01">
            Advertencia: se rechazará la solicitud de {solicitudARechazar.nombre} ({solicitudARechazar.login}). Si ya
            tenía un código sin usar, dejará de valer.
          </p>
        )}
      </Dialogo>

      <Dialogo
        abierto={aprobada !== null}
        titulo="Código de activación"
        alCerrar={cerrarDialogoCodigo}
        pie={
          <Button key="cerrar" kind="primary" size="md" type="button" onClick={cerrarDialogoCodigo}>
            Cerrar
          </Button>
        }
      >
        {aprobada && (
          <div className="silice-adm__dialogo-codigo">
            <p className="cds--type-body-compact-01">
              Entregue este código a <strong>{aprobada.nombre}</strong> ({aprobada.login}):
            </p>
            <p className="silice-adm__codigo-unico">{aprobada.codigo}</p>
            <p className="cds--type-body-compact-01">Vence el {vencimientoEsVe(aprobada.vence)}.</p>
            <p className="silice-adm__nota cds--type-body-compact-01">Este código no se vuelve a mostrar</p>
            <div className="silice-adm__acciones">
              <Button
                kind="secondary"
                size="md"
                type="button"
                data-autofocus
                onClick={() => void copiarCodigo()}
              >
                Copiar el código
              </Button>
              <a href={aprobada.mailto} className="cds--btn cds--btn--secondary cds--btn--md silice-adm__enlace-correo">
                Enviarlo por correo
              </a>
            </div>
            {estadoCopia === "ok" && (
              <p role="status" className="cds--type-label-01">
                Información: Código copiado al portapapeles.
              </p>
            )}
            {estadoCopia === "error" && (
              <InlineNotification
                kind="warning"
                role="alert"
                title="Advertencia: no se pudo copiar el código"
                subtitle="Seleccione el código de arriba y cópielo manualmente."
                lowContrast
                hideCloseButton
              />
            )}
          </div>
        )}
      </Dialogo>
    </div>
  );
}
