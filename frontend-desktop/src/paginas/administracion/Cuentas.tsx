import { Button, Checkbox, InlineNotification, Select, SelectItem, TextInput } from "@carbon/react";
import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { AvisoError } from "../../comun/AvisoError";
import { TablaDensa } from "../../comun/TablaDensa";
import { useAplicacion } from "../../shell/contexto";
import { AVISO_TEMPORAL, CONFIRMACIONES, ROLES, avisoDeRoles, etiquetaDeRol, filasDeCuentas } from "./logica";
import type { Cuenta, CuentasRespuesta, ResultadoCuenta } from "./logica";

type Resultado = { tipo: "ok"; mensaje: string; aviso: string | null } | { tipo: "error"; error: unknown };

function SelectorDeRoles({
  idBase,
  leyenda,
  elegidos,
  alCambiar,
}: {
  idBase: string;
  leyenda: string;
  elegidos: string[];
  alCambiar: (roles: string[]) => void;
}) {
  return (
    <fieldset className="cds--fieldset">
      <legend className="cds--label">{leyenda}</legend>
      {ROLES.map((rol) => (
        <Checkbox
          key={rol}
          id={`${idBase}-${rol}`}
          labelText={etiquetaDeRol(rol)}
          checked={elegidos.includes(rol)}
          onChange={(_, { checked }) => alCambiar(checked ? [...elegidos, rol] : elegidos.filter((r) => r !== rol))}
        />
      ))}
    </fieldset>
  );
}

// Confirmacion explicita en la misma pagina. No usa el Modal de Carbon: su archivo trae una URL de documentacion que
// `npm run dist` rechaza (RNF-22: ninguna URL a otro anfitrion). El foco pasa al aviso y Escape cancela.
function Confirmacion({
  titulo,
  texto,
  boton,
  peligro,
  alConfirmar,
  alCancelar,
}: {
  titulo: string;
  texto: string;
  boton: string;
  peligro: boolean;
  alConfirmar: () => void;
  alCancelar: () => void;
}) {
  const caja = useRef<HTMLDivElement>(null);
  useEffect(() => {
    caja.current?.focus();
  }, []);
  return (
    <div
      ref={caja}
      role="alertdialog"
      aria-labelledby="adm-confirmar-titulo"
      aria-describedby="adm-confirmar-texto"
      tabIndex={-1}
      className="silice-adm__confirmar"
      onKeyDown={(e) => {
        if (e.key === "Escape") alCancelar();
      }}
    >
      <h3 id="adm-confirmar-titulo" className="cds--type-heading-compact-01">
        {titulo}
      </h3>
      <p id="adm-confirmar-texto" className="cds--type-body-compact-01">
        {texto}
      </p>
      <div className="silice-adm__acciones">
        <Button kind={peligro ? "danger" : "primary"} size="md" onClick={alConfirmar}>
          {boton}
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
// (con exito o sin el), como los formularios de Streamlit; la API nunca las devuelve. Al cambiar de pestana el
// componente se desmonta y no queda nada.
export default function Cuentas() {
  const { alExpirar } = useAplicacion();
  const [lista, setLista] = useState<CuentasRespuesta | null>(null);
  const [errorDeLista, setErrorDeLista] = useState<unknown>(null);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const aviso = useRef<HTMLDivElement>(null);

  const [login, setLogin] = useState("");
  const [nombre, setNombre] = useState("");
  const [rolesNuevos, setRolesNuevos] = useState<string[]>([]);
  const [temporal, setTemporal] = useState("");

  const [elegidaId, setElegidaId] = useState<number | null>(null);
  const [nueva, setNueva] = useState("");
  const [confirmar, setConfirmar] = useState<"desactivar" | "restablecer" | null>(null);

  const cuentas = lista?.cuentas ?? [];
  const elegida: Cuenta | undefined = cuentas.find((c) => c.id === elegidaId) ?? cuentas[0];

  const cargar = useCallback(async () => {
    try {
      setLista(await pedir<CuentasRespuesta>("/v1/cuentas"));
      setErrorDeLista(null);
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setErrorDeLista(e);
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

  // Al cambiar de cuenta (o recargar la lista) los roles editados vuelven a los de la cuenta.
  const clave = `${elegida?.id ?? ""}:${elegida?.roles.join(",") ?? ""}`;
  const [edicion, setEdicion] = useState<{ clave: string; roles: string[] }>({ clave, roles: elegida?.roles ?? [] });
  if (edicion.clave !== clave) setEdicion({ clave, roles: elegida?.roles ?? [] });
  const rolesEditados = edicion.roles;
  const setRolesEditados = (roles: string[]) => setEdicion({ clave, roles });

  // Tras cada accion el foco va al resultado.
  useEffect(() => {
    if (resultado) aviso.current?.focus();
  }, [resultado]);

  // Manda una accion; devuelve true si la API la acepto. Recarga la lista despues.
  const ejecutar = async (ruta: string, cuerpo: object): Promise<boolean> => {
    setOcupado(true);
    setResultado(null);
    try {
      const r = await pedir<ResultadoCuenta>(ruta, { metodo: "POST", cuerpo });
      setResultado({ tipo: "ok", mensaje: r.mensaje, aviso: r.aviso });
      await cargar();
      return true;
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
      setResultado({ tipo: "error", error: e });
      return false;
    } finally {
      setOcupado(false);
    }
  };

  const crear = async (evento: FormEvent) => {
    evento.preventDefault();
    const cuerpo = { login, nombre, roles: rolesNuevos, contrasena_temporal: temporal };
    setTemporal(""); // se vacia al enviar, haya exito o no
    if (await ejecutar("/v1/cuentas", cuerpo)) {
      setLogin("");
      setNombre("");
      setRolesNuevos([]);
    }
  };

  const restablecer = async () => {
    if (!elegida) return;
    const cuerpo = { contrasena_temporal: nueva };
    setNueva("");
    setConfirmar(null);
    await ejecutar(`/v1/cuentas/${elegida.id}/restablecer`, cuerpo);
  };

  const desactivar = async () => {
    if (!elegida) return;
    setConfirmar(null);
    await ejecutar(`/v1/cuentas/${elegida.id}/desactivar`, {});
  };

  const avisoEnEdicion = lista ? avisoDeRoles(rolesEditados, lista.aviso_arma_y_revisa) : null;
  const avisoEnAlta = lista ? avisoDeRoles(rolesNuevos, lista.aviso_arma_y_revisa) : null;

  return (
    <div className="silice-adm__secciones">
      <section aria-labelledby="adm-cuentas" className="silice-adm__tabla">
        <h2 id="adm-cuentas" className="cds--type-heading-03">
          Cuentas
        </h2>
        <AvisoError error={errorDeLista} titulo="No se pudieron leer las cuentas" />
        {errorDeLista === null && (
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

      <div aria-live="polite" aria-atomic="true">
        <div ref={aviso} tabIndex={-1} className="silice-adm__resultado">
          {resultado?.tipo === "ok" && (
            <>
              <InlineNotification kind="success" role="status" title="Hecho" subtitle={resultado.mensaje} lowContrast hideCloseButton />
              {resultado.aviso && (
                <InlineNotification kind="warning" role="status" title="Aviso" subtitle={resultado.aviso} lowContrast hideCloseButton />
              )}
            </>
          )}
          {resultado?.tipo === "error" && <AvisoError error={resultado.error} />}
        </div>
      </div>

      <section aria-labelledby="adm-crear" className="silice-adm__seccion">
        <h2 id="adm-crear" className="cds--type-heading-03">
          Crear una cuenta
        </h2>
        <form className="silice-adm__seccion" onSubmit={(e) => void crear(e)} autoComplete="off">
          <TextInput id="adm-login" labelText="Usuario (minúsculas, sin espacios)" value={login} onChange={(e) => setLogin(e.target.value)} />
          <TextInput id="adm-nombre" labelText="Nombre de la persona" value={nombre} onChange={(e) => setNombre(e.target.value)} />
          <SelectorDeRoles idBase="adm-roles" leyenda="Qué puede hacer" elegidos={rolesNuevos} alCambiar={setRolesNuevos} />
          {avisoEnAlta && <p className="silice-adm__nota cds--type-label-01">{avisoEnAlta}</p>}
          <TextInput
            id="adm-temporal"
            type="password"
            autoComplete="new-password"
            labelText="Contraseña temporal (10 a 128 caracteres)"
            helperText={AVISO_TEMPORAL}
            value={temporal}
            onChange={(e) => setTemporal(e.target.value)}
          />
          <div>
            <Button type="submit" kind="primary" size="md" disabled={ocupado}>
              Crear la cuenta
            </Button>
          </div>
        </form>
      </section>

      {elegida && (
        <section aria-labelledby="adm-cambiar" className="silice-adm__seccion">
          <h2 id="adm-cambiar" className="cds--type-heading-03">
            Cambiar una cuenta
          </h2>
          <Select id="adm-cuenta" labelText="Cuenta" value={String(elegida.id)} onChange={(e) => setElegidaId(Number(e.target.value))}>
            {cuentas.map((c) => (
              <SelectItem key={c.id} value={String(c.id)} text={c.login} />
            ))}
          </Select>
          <SelectorDeRoles idBase="adm-roles-de" leyenda="Qué puede hacer la cuenta" elegidos={rolesEditados} alCambiar={setRolesEditados} />
          {avisoEnEdicion && <p className="silice-adm__nota cds--type-label-01">{avisoEnEdicion}</p>}
          <div className="silice-adm__acciones">
            <Button kind="secondary" size="md" disabled={ocupado} onClick={() => void ejecutar(`/v1/cuentas/${elegida.id}/roles`, { roles: rolesEditados })}>
              Guardar roles
            </Button>
            {elegida.activa ? (
              <Button kind="danger--tertiary" size="md" disabled={ocupado} onClick={() => setConfirmar("desactivar")}>
                Desactivar
              </Button>
            ) : (
              <Button kind="secondary" size="md" disabled={ocupado} onClick={() => void ejecutar(`/v1/cuentas/${elegida.id}/reactivar`, {})}>
                Reactivar
              </Button>
            )}
            <Button kind="secondary" size="md" disabled={ocupado} onClick={() => void ejecutar(`/v1/cuentas/${elegida.id}/desbloquear`, {})}>
              Desbloquear
            </Button>
          </div>
          <form
            className="silice-adm__seccion"
            autoComplete="off"
            onSubmit={(e) => {
              e.preventDefault();
              setConfirmar("restablecer");
            }}
          >
            <TextInput
              id="adm-restablecer"
              type="password"
              autoComplete="new-password"
              labelText="Contraseña temporal nueva"
              value={nueva}
              onChange={(e) => setNueva(e.target.value)}
            />
            <div>
              <Button type="submit" kind="tertiary" size="md" disabled={ocupado || nueva === ""}>
                Restablecer la contraseña
              </Button>
            </div>
          </form>
        </section>
      )}

      {confirmar && elegida && (
        <Confirmacion
          titulo={CONFIRMACIONES[confirmar].titulo}
          texto={CONFIRMACIONES[confirmar].texto(elegida.login)}
          boton={CONFIRMACIONES[confirmar].boton}
          peligro={confirmar === "desactivar"}
          alConfirmar={() => void (confirmar === "desactivar" ? desactivar() : restablecer())}
          alCancelar={() => setConfirmar(null)}
        />
      )}
    </div>
  );
}
