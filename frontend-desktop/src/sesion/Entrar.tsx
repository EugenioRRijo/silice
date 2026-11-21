import { Button, Form } from "@carbon/react";
import { InlineNotification, PasswordInput } from "../comun/carbonEs";
import { useState } from "react";
import type { FormEvent } from "react";
import { mensajeDeError } from "../comun/errores";
import { useTituloDelDocumento } from "../comun/tituloDelDocumento";
import { CampoTexto } from "../comun/CampoTexto";

interface Props {
  onEntrar: (login: string, contrasena: string) => Promise<void>;
  // Para decir por que se volvio a esta pantalla (por ejemplo, la sesion vencio).
  aviso?: string;
  // Con cuentas creadas: lleva a la pantalla de «recuperar acceso» con un código de restablecimiento (BCP-4). Sin él,
  // el enlace no se pinta.
  alRecuperar?: () => void;
}

export function Entrar({ onEntrar, aviso, alRecuperar }: Props) {
  useTituloDelDocumento("Entrar");
  const [login, setLogin] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [intentado, setIntentado] = useState(false);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setIntentado(true);
    if (!login.trim() || !contrasena) return;
    setEnviando(true);
    setError(null);
    try {
      await onEntrar(login.trim(), contrasena);
    } catch (e) {
      setError(mensajeDeError(e));
      setEnviando(false);
    }
  }

  return (
    <main className="silice-entrada silice-entrada--dividida">
      <div className="silice-entrada__rejilla">
        <aside className="silice-entrada__marca-panel">
          <div className="silice-entrada__sello">S</div>
          <div className="silice-entrada__marca-cuerpo">
            <h2 className="cds--type-heading-04">Sílice</h2>
            <p className="silice-entrada__marca-texto">
              Ingeniería de costos, presupuestos APU y auditoría forense de libros Excel sobre base
              local verificable.
            </p>
          </div>
          <dl className="silice-entrada__fichas">
            <div className="silice-entrada__ficha">
              <dt className="silice-entrada__clave">Acceso único</dt>
              <dd className="silice-entrada__valor">
                Usuario y contraseña para cuentas operativas o administrador de la instalación.
              </dd>
            </div>
            <div className="silice-entrada__ficha">
              <dt className="silice-entrada__clave">Entorno local</dt>
              <dd className="silice-entrada__valor">
                Sesión de prueba web conectada al servidor SQLite local.
              </dd>
            </div>
          </dl>
        </aside>
        <section className="silice-entrada__panel">
          <h1 className="cds--type-heading-04">Entrar</h1>
          <p className="silice-entrada__texto cds--type-body-compact-01">
            Entre con su usuario y contraseña de Sílice.
          </p>
          {aviso && <p className="silice-entrada__aviso cds--type-body-compact-01">{aviso}</p>}
          <Form className="silice-entrada__formulario" onSubmit={enviar} noValidate>
            <CampoTexto
              id="entrar-usuario"
              labelText="Usuario"
              autoComplete="username"
              value={login}
              onChange={(e) => setLogin(e.target.value)}
              invalid={intentado && !login.trim()}
              invalidText="Escriba su usuario."
            />
            <PasswordInput
              id="entrar-contrasena"
              labelText="Contraseña"
              autoComplete="current-password"
              value={contrasena}
              onChange={(e) => setContrasena(e.target.value)}
              invalid={intentado && !contrasena}
              invalidText="Escriba su contraseña."
            />
            {error && (
              <InlineNotification
                kind="error"
                role="alert"
                title="No se pudo entrar"
                subtitle={error}
                hideCloseButton
                lowContrast
              />
            )}
            <div className="silice-entrada__acciones">
              <Button type="submit" disabled={enviando} className="silice-entrada__enviar">
                {enviando ? "Entrando…" : "Entrar"}
              </Button>
              {alRecuperar && (
                <Button kind="ghost" size="sm" type="button" onClick={alRecuperar}>
                  Perdí el acceso de administrador
                </Button>
              )}
            </div>
          </Form>
        </section>
      </div>
    </main>
  );
}
