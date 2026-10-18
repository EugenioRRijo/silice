import { Button, Form, InlineNotification, PasswordInput, TextInput } from "@carbon/react";
import { useState } from "react";
import type { FormEvent } from "react";
import { ErrorDeApi } from "../api/cliente";

interface Props {
  onEntrar: (login: string, contrasena: string) => Promise<void>;
  // Para decir por que se volvio a esta pantalla (por ejemplo, la sesion vencio).
  aviso?: string;
}

function mensajeDe(error: unknown): string {
  if (error instanceof ErrorDeApi) {
    const espera = error.reintentarEnSegundos;
    if (error.estado === 429 && espera !== null) {
      const unidad = espera === 1 ? "segundo" : "segundos";
      return `${error.detalle} Espere ${espera} ${unidad} antes de volver a intentarlo.`;
    }
    return error.detalle;
  }
  return "Ocurrió un error inesperado. Inténtelo de nuevo.";
}

export function Entrar({ onEntrar, aviso }: Props) {
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
      setError(mensajeDe(e));
      setEnviando(false);
    }
  }

  return (
    <main className="silice-entrada">
      <h1 className="cds--type-heading-03">Entrar</h1>
      <p className="silice-entrada__texto cds--type-body-compact-01">
        Entre con su cuenta de Sílice para ver y auditar el libro de presupuesto de la empresa.
      </p>
      {aviso && <p className="silice-entrada__texto cds--type-body-compact-01">{aviso}</p>}
      <Form className="silice-entrada__formulario" onSubmit={enviar} noValidate>
        <TextInput
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
      </Form>
    </main>
  );
}
