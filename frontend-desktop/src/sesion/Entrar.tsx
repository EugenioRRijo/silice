import { Button, Form } from "@carbon/react";
import { CheckmarkFilled, Password } from "@carbon/icons-react";
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
          <div className="silice-entrada__marca-arriba">
            <p className="silice-entrada__etiqueta">Instalación local · SQLite</p>
            <h2 className="silice-entrada__marca-titulo">
              Entrar al escritorio de presupuestos y auditoría
            </h2>
            <p className="silice-entrada__marca-texto">
              Cada sesión aplica control de roles separado entre quien arma, revisa, aprueba y
              administra la carpeta local.
            </p>
          </div>

          <dl className="silice-entrada__fichas">
            <div className="silice-entrada__ficha">
              <dt className="silice-entrada__clave">Separación de funciones (RBAC)</dt>
              <dd className="silice-entrada__valor">
                Quien elabora el presupuesto no aprueba ni firma su propio paquete de entrega.
              </dd>
            </div>
            <div className="silice-entrada__ficha">
              <dt className="silice-entrada__clave">Aritmética Decimal exacta</dt>
              <dd className="silice-entrada__valor">
                Cálculos APU, auditoría de libros Excel y firmas locales sobre tu propio equipo.
              </dd>
            </div>
          </dl>
        </aside>

        <section className="silice-entrada__panel">
          <div className="silice-entrada__cabecera">
            <h1 className="cds--type-heading-04">Entrar</h1>
            <p className="silice-entrada__texto cds--type-body-compact-01">
              Usa tu cuenta registrada en <code className="silice-codigo">instalacion.db</code>.
            </p>
          </div>
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
              <Button
                type="submit"
                disabled={enviando}
                renderIcon={Password}
                className="silice-entrada__enviar"
              >
                {enviando ? "Entrando…" : "Entrar"}
              </Button>
              {alRecuperar && (
                <Button kind="ghost" size="sm" type="button" onClick={alRecuperar}>
                  Perdí el acceso de administrador
                </Button>
              )}
            </div>
          </Form>
          <div className="silice-entrada__pie-seguridad">
            <CheckmarkFilled size={16} aria-hidden="true" />
            <span>Sesión local cifrada · Sin envío de datos externos</span>
          </div>
        </section>
      </div>
    </main>
  );
}
