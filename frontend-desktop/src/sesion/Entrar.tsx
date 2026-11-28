import { Button, Form } from "@carbon/react";
import { Password } from "@carbon/icons-react";
import { InlineNotification, PasswordInput } from "../comun/carbonEs";
import { useState } from "react";
import type { FormEvent } from "react";
import { mensajeDeError } from "../comun/errores";
import { useTituloDelDocumento } from "../comun/tituloDelDocumento";
import { CampoTexto } from "../comun/CampoTexto";
import { CrearCuenta } from "./CrearCuenta";
import { TengoUnCodigo } from "./TengoUnCodigo";
import "./sesion.scss";

type VistaDeEntrada = "entrar" | "crear" | "canjear";

const TITULOS_DE_VISTA: Record<VistaDeEntrada, string> = {
  entrar: "Entrar",
  crear: "Crear una cuenta",
  canjear: "Tengo un código",
};

interface Props {
  onEntrar: (login: string, contrasena: string) => Promise<void>;
  // Para decir por que se volvio a esta pantalla (por ejemplo, la sesion vencio).
  aviso?: string;
  // Con cuentas creadas: lleva a la pantalla de «recuperar acceso» con un código de restablecimiento (BCP-4). Sin él,
  // el enlace no se pinta.
  alRecuperar?: () => void;
  onCanjear?: (login: string, contrasena: string, codigo: string) => Promise<void>;
}

export function Entrar({ onEntrar, aviso, alRecuperar, onCanjear }: Props) {
  const [vista, setVista] = useState<VistaDeEntrada>("entrar");
  useTituloDelDocumento(TITULOS_DE_VISTA[vista]);
  const [login, setLogin] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [intentado, setIntentado] = useState(false);

  if (vista === "crear") {
    return <CrearCuenta alVolver={() => setVista("entrar")} alIrACanjear={() => setVista("canjear")} />;
  }

  if (vista === "canjear") {
    return <TengoUnCodigo onCanjear={onCanjear} alVolver={() => setVista("entrar")} />;
  }

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
            <p className="silice-entrada__etiqueta">Instalación local</p>
            <h2 className="silice-entrada__marca-titulo">
              Entrar al escritorio de presupuestos y auditoría
            </h2>
            <p className="silice-entrada__marca-texto">
              Cada cuenta entra con sus roles (arma, revisa o administra) y hace lo que esos roles le
              permiten.
            </p>
          </div>

          <dl className="silice-entrada__fichas">
            <div className="silice-entrada__ficha">
              <dt className="silice-entrada__clave">Quien arma y quien revisa</dt>
              <dd className="silice-entrada__valor">
                Si quien revisa una versión también la armó, la revisión lo avisa y el dictamen queda registrado.
              </dd>
            </div>
            <div className="silice-entrada__ficha">
              <dt className="silice-entrada__clave">Cálculo exacto de precios</dt>
              <dd className="silice-entrada__valor">
                Cálculos de APU, auditoría de libros Excel y firmas locales en este equipo.
              </dd>
            </div>
          </dl>
        </aside>

        <section className="silice-entrada__panel">
          <div className="silice-entrada__cabecera">
            <h1 className="cds--type-heading-04">Entrar</h1>
            <p className="silice-entrada__texto cds--type-body-compact-01">
              Escriba el usuario y la contraseña de su cuenta en esta instalación.
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
          <div className="silice-entrada__enlaces">
            <Button kind="ghost" size="sm" type="button" onClick={() => setVista("crear")}>
              Crear una cuenta
            </Button>
            <Button kind="ghost" size="sm" type="button" onClick={() => setVista("canjear")}>
              Tengo un código
            </Button>
          </div>
          <div className="silice-entrada__pie-seguridad">
            <span>La sesión vive en el servidor de Sílice de esta instalación · El asistente con un proveedor en la nube viene apagado</span>
          </div>
        </section>
      </div>
    </main>
  );
}
