import { Button, Checkbox, InlineNotification, PasswordInput, Select, SelectItem } from "@carbon/react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { CampoTexto } from "../../comun/CampoTexto";
import { TablaDensa } from "../../comun/TablaDensa";
import { mensajeDeError } from "../../comun/errores";
import { useAplicacion } from "../../shell/contexto";
import {
  AVISO_TEMPORAL,
  AYUDA_CONTRASENA,
  AYUDA_DESBLOQUEAR,
  AYUDA_USUARIO,
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

function SelectorDeRoles({
  idBase,
  leyenda,
  elegidos,
  alCambiar,
  deshabilitado = false,
}: {
  idBase: string;
  leyenda: string;
  elegidos: string[];
  alCambiar: (roles: string[]) => void;
  deshabilitado?: boolean;
}) {
  return (
    <fieldset className="cds--fieldset" disabled={deshabilitado}>
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

// Pestana «Cuentas» (accion ADMINISTRAR_CUENTAS): lista, alta, roles, desactivar/reactivar, desbloquear y
// restablecer la contrasena. Las contrasenas viven solo en el estado de este componente y se vacian al enviar
// (con exito o sin el) o al cancelar, como los formularios de Streamlit; la API nunca las devuelve. Al cambiar de
// pestana el componente se desmonta y no queda nada. El resultado se anuncia con el foco (no con aria-live).
export default function Cuentas() {
  const { alExpirar, sesion } = useAplicacion();
  const [lista, setLista] = useState<CuentasRespuesta | null>(null);
  const [errorDeLista, setErrorDeLista] = useState<unknown>(null);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const aviso = useRef<HTMLDivElement>(null);
  const montado = useRef(true);
  const quienAbrio = useRef<HTMLElement | null>(null);

  const [login, setLogin] = useState("");
  const [nombre, setNombre] = useState("");
  const [rolesNuevos, setRolesNuevos] = useState<string[]>([]);
  const [temporal, setTemporal] = useState("");

  const [elegidaId, setElegidaId] = useState<number | null>(null);
  const [nueva, setNueva] = useState("");
  const [pendiente, setPendiente] = useState<Pendiente | null>(null);

  const cuentas = lista?.cuentas ?? [];
  const elegida: Cuenta | undefined = cuentas.find((c) => c.id === elegidaId);

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
    if (!puedeCrear(login, nombre, temporal)) return;
    const cuerpo = { login, nombre, roles: rolesNuevos, contrasena_temporal: temporal };
    setTemporal(""); // se vacia al enviar, haya exito o no
    if (await ejecutar("/v1/cuentas", cuerpo) && montado.current) {
      setLogin("");
      setNombre("");
      setRolesNuevos([]);
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
            ]}
            filas={filasDeCuentas(cuentas)}
            vacio={{ titulo: "Todavía no hay cuentas." }}
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
            value={login}
            onChange={(e) => setLogin(e.target.value)}
          />
          <CampoTexto id="adm-nombre" labelText="Nombre de la persona" required value={nombre} onChange={(e) => setNombre(e.target.value)} />
          <SelectorDeRoles idBase="adm-roles" leyenda="Qué puede hacer" elegidos={rolesNuevos} alCambiar={setRolesNuevos} />
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
            <Button type="submit" kind="primary" size="md" disabled={ocupado || !puedeCrear(login, nombre, temporal)}>
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
    </div>
  );
}
