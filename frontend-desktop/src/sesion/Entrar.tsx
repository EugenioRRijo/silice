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
  const [modo, setModo] = useState<"usuario" | "master">("usuario");
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
        <aside className="silice-entrada__contexto">
          <div className="silice-entrada__modos" role="group" aria-label="Modo de acceso">
            <button
              type="button"
              className="silice-entrada__modo"
              aria-pressed={modo === "usuario"}
              onClick={() => setModo("usuario")}
            >
              Acceso de usuario (Arma / Revisa)
            </button>
            <button
              type="button"
              className="silice-entrada__modo"
              aria-pressed={modo === "master"}
              onClick={() => setModo("master")}
            >
              Administrador Master
            </button>
          </div>
          {modo === "usuario" ? (
            <div className="silice-entrada__detalle">
              <p className="cds--type-label-01">Operación por roles asignados</p>
              <ul className="silice-entrada__lista">
                <li>
                  <strong>[ROL ARMA]</strong> Elabora presupuestos, edita APU, guarda versiones y ejecuta simulaciones.
                </li>
                <li>
                  <strong>[ROL REVISA]</strong> Audita libros Excel, verifica trazabilidad y aprueba o devuelve entregas.
                </li>
              </ul>
            </div>
          ) : (
            <div className="silice-entrada__detalle">
              <p className="cds--type-label-01">Consola de administración local</p>
              <ul className="silice-entrada__lista">
                <li>Almacenamiento: SQLite local</li>
                <li>Gobernanza: Cuentas y roles</li>
                <li>Integridad: SHA-256 + Argon2id</li>
              </ul>
            </div>
          )}
        </aside>
        <section className="silice-entrada__panel">
          <h1 className="cds--type-heading-04">Entrar</h1>
          <p className="silice-entrada__texto cds--type-body-compact-01">
            {modo === "master"
              ? "Acceso de consola raíz para administrar cuentas, respaldos e instalación."
              : "Entre con su cuenta de Sílice para ver y auditar el libro de presupuesto de la empresa."}
          </p>
          {aviso && <p className="silice-entrada__texto cds--type-body-compact-01">{aviso}</p>}
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
            <Button type="submit" disabled={enviando}>
              {enviando ? "Entrando…" : "Entrar"}
            </Button>
            {alRecuperar && (
              <Button kind="ghost" size="sm" type="button" onClick={alRecuperar}>
                Perdí el acceso de administrador
              </Button>
            )}
          </Form>
        </section>
      </div>
    </main>
  );
}
