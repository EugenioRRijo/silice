import { Button, Form } from "@carbon/react";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi, pedir } from "../api/cliente";
import { CampoTexto } from "../comun/CampoTexto";
import { InlineNotification, PasswordInput } from "../comun/carbonEs";
import { mensajeDeError } from "../comun/errores";
import { useTituloDelDocumento } from "../comun/tituloDelDocumento";
import "./sesion.scss";

interface Props {
  alVolver: () => void;
  alIrACanjear: () => void;
}

interface RespuestaSolicitud {
  mensaje: string;
}

type CampoDeSolicitud = "nombre" | "correo" | "login" | "contrasena" | "confirmacion";

const ID_CAMPO: Record<CampoDeSolicitud, string> = {
  nombre: "crear-nombre",
  correo: "crear-correo",
  login: "crear-usuario",
  contrasena: "crear-contrasena",
  confirmacion: "crear-confirmacion",
};

function campoDelErrorDelServidor(error: unknown): Exclude<CampoDeSolicitud, "confirmacion"> | null {
  if (!(error instanceof ErrorDeApi)) return null;
  if (error.estado === 409) return "login";
  if (error.estado !== 422) return null;
  if (
    error.campo === "nombre" ||
    error.campo === "correo" ||
    error.campo === "login" ||
    error.campo === "contrasena"
  ) {
    return error.campo;
  }
  const detalle = error.detalle.toLowerCase();
  if (detalle.includes("nombre") && detalle.includes("correo") && detalle.includes("usuario")) return null;
  if (detalle.includes("contraseña")) return "contrasena";
  if (detalle.includes("correo")) return "correo";
  if (detalle.includes("usuario")) return "login";
  if (detalle.includes("nombre")) return "nombre";
  return null;
}

export function CrearCuenta({ alVolver, alIrACanjear }: Props) {
  useTituloDelDocumento("Crear una cuenta");
  const [nombre, setNombre] = useState("");
  const [correo, setCorreo] = useState("");
  const [login, setLogin] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [intentado, setIntentado] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [mensajeEnviado, setMensajeEnviado] = useState<string | null>(null);
  const [errorDeCampo, setErrorDeCampo] = useState<{
    campo: Exclude<CampoDeSolicitud, "confirmacion">;
    mensaje: string;
  } | null>(null);
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);

  const focoPendiente = useRef<
    { tipo: "campo"; campo: CampoDeSolicitud } | { tipo: "alerta" } | { tipo: "confirmacion" } | null
  >(null);
  const refAlerta = useRef<HTMLDivElement>(null);
  const refConfirmacion = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const objetivo = focoPendiente.current;
    if (objetivo === null) return;
    focoPendiente.current = null;
    if (objetivo.tipo === "campo") {
      document.getElementById(ID_CAMPO[objetivo.campo])?.focus();
    } else if (objetivo.tipo === "alerta") {
      refAlerta.current?.focus();
    } else {
      refConfirmacion.current?.focus();
    }
  });

  const noCoincide = confirmacion !== "" && confirmacion !== contrasena;
  const sinConfirmar = intentado && confirmacion === "";

  const errorLocal = (campo: CampoDeSolicitud): string | null => {
    if (!intentado) {
      if (campo === "confirmacion" && noCoincide) return "Las contraseñas no coinciden.";
      return null;
    }
    if (campo === "nombre" && !nombre.trim()) return "Escriba su nombre.";
    if (campo === "correo" && !correo.trim()) return "Escriba su correo.";
    if (campo === "login" && !login.trim()) return "Escriba su usuario.";
    if (campo === "contrasena" && !contrasena) return "Escriba su contraseña.";
    if (campo === "confirmacion") {
      if (sinConfirmar) return "Confirme la contraseña.";
      if (noCoincide) return "Las contraseñas no coinciden.";
    }
    return null;
  };

  const mensajeDeCampo = (campo: Exclude<CampoDeSolicitud, "confirmacion">): string | null => {
    if (errorDeCampo?.campo === campo) return errorDeCampo.mensaje;
    return errorLocal(campo);
  };

  const limpiarErrorDe = (campo: Exclude<CampoDeSolicitud, "confirmacion">) => {
    if (errorDeCampo?.campo === campo) setErrorDeCampo(null);
  };

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (enviando) return;
    setIntentado(true);
    setErrorDeCampo(null);
    setErrorGeneral(null);

    const orden: CampoDeSolicitud[] = ["nombre", "correo", "login", "contrasena", "confirmacion"];
    const primerInvalido = orden.find((campo) => {
      if (campo === "nombre") return !nombre.trim();
      if (campo === "correo") return !correo.trim();
      if (campo === "login") return !login.trim();
      if (campo === "contrasena") return !contrasena;
      return !confirmacion || confirmacion !== contrasena;
    });
    if (primerInvalido !== undefined) {
      focoPendiente.current = { tipo: "campo", campo: primerInvalido };
      document.getElementById(ID_CAMPO[primerInvalido])?.focus();
      return;
    }

    const cuerpo = {
      nombre: nombre.trim(),
      correo: correo.trim(),
      login: login.trim(),
      contrasena,
    };
    setEnviando(true);
    // La contraseña no permanece en el estado después de enviar, haya éxito o error.
    setContrasena("");
    setConfirmacion("");
    setIntentado(false);

    try {
      const respuesta = await pedir<RespuestaSolicitud>("/v1/solicitudes", {
        metodo: "POST",
        cuerpo,
      });
      focoPendiente.current = { tipo: "confirmacion" };
      setMensajeEnviado(respuesta.mensaje);
    } catch (error) {
      const campo = campoDelErrorDelServidor(error);
      const mensaje = mensajeDeError(error);
      if (campo !== null) {
        focoPendiente.current = { tipo: "campo", campo };
        setErrorDeCampo({ campo, mensaje });
      } else {
        focoPendiente.current = { tipo: "alerta" };
        setErrorGeneral(mensaje);
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className="silice-entrada">
      <section className="silice-entrada__secundaria">
        <div className="silice-entrada__cabecera">
          <h1 className="cds--type-heading-04">Crear una cuenta</h1>
          <p className="silice-entrada__texto cds--type-body-compact-01">
            Envíe sus datos para que quien administra esta instalación apruebe su solicitud y le envíe un código de 20
            caracteres a su correo.
          </p>
        </div>

        {mensajeEnviado !== null ? (
          <div ref={refConfirmacion} tabIndex={-1} className="silice-entrada__confirmacion silice-entrada__aviso-foco">
            <InlineNotification
              kind="success"
              role="status"
              title="Información: solicitud enviada"
              subtitle={mensajeEnviado}
              lowContrast
              hideCloseButton
            />
            <div className="silice-entrada__enlaces">
              <Button kind="primary" type="button" onClick={alIrACanjear}>
                Ya tengo el código
              </Button>
              <Button kind="ghost" size="sm" type="button" onClick={alVolver}>
                Volver
              </Button>
            </div>
          </div>
        ) : (
          <Form className="silice-entrada__formulario" onSubmit={(e) => void enviar(e)} noValidate>
            {errorGeneral !== null && (
              <div ref={refAlerta} tabIndex={-1} className="silice-entrada__aviso-foco">
                <InlineNotification
                  kind="error"
                  role="alert"
                  title="Error: no se pudo enviar la solicitud"
                  subtitle={errorGeneral}
                  lowContrast
                  hideCloseButton
                />
              </div>
            )}
            <CampoTexto
              id={ID_CAMPO.nombre}
              labelText="Nombre"
              autoComplete="name"
              value={nombre}
              onChange={(e) => {
                setNombre(e.target.value);
                limpiarErrorDe("nombre");
              }}
              invalid={mensajeDeCampo("nombre") !== null}
              invalidText={mensajeDeCampo("nombre") ?? ""}
            />
            <CampoTexto
              id={ID_CAMPO.correo}
              type="email"
              labelText="Correo"
              helperText="Ejemplo: nombre@empresa.com"
              autoComplete="email"
              spellCheck={false}
              value={correo}
              onChange={(e) => {
                setCorreo(e.target.value);
                limpiarErrorDe("correo");
              }}
              invalid={mensajeDeCampo("correo") !== null}
              invalidText={mensajeDeCampo("correo") ?? ""}
            />
            <CampoTexto
              id={ID_CAMPO.login}
              labelText="Usuario"
              helperText="De 3 a 40 caracteres: letras sin tilde, números, punto o guion."
              autoComplete="username"
              autoCapitalize="none"
              spellCheck={false}
              value={login}
              onChange={(e) => {
                setLogin(e.target.value);
                limpiarErrorDe("login");
              }}
              invalid={mensajeDeCampo("login") !== null}
              invalidText={mensajeDeCampo("login") ?? ""}
            />
            <PasswordInput
              id={ID_CAMPO.contrasena}
              labelText="Contraseña"
              helperText="De 10 a 128 caracteres, distinta de su usuario."
              autoComplete="new-password"
              value={contrasena}
              onChange={(e) => {
                setContrasena(e.target.value);
                limpiarErrorDe("contrasena");
              }}
              invalid={mensajeDeCampo("contrasena") !== null}
              invalidText={mensajeDeCampo("contrasena") ?? ""}
            />
            <PasswordInput
              id={ID_CAMPO.confirmacion}
              labelText="Confirme la contraseña"
              autoComplete="new-password"
              value={confirmacion}
              onChange={(e) => setConfirmacion(e.target.value)}
              invalid={errorLocal("confirmacion") !== null}
              invalidText={errorLocal("confirmacion") ?? ""}
            />
            <div className="silice-entrada__acciones">
              <Button type="submit" disabled={enviando} className="silice-entrada__enviar">
                {enviando ? "Enviando la solicitud…" : "Enviar la solicitud"}
              </Button>
              <Button kind="ghost" size="sm" type="button" onClick={alVolver}>
                Volver
              </Button>
            </div>
          </Form>
        )}
      </section>
    </main>
  );
}
