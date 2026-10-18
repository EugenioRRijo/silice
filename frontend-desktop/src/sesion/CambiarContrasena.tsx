import { Button, Form, PasswordInput } from "@carbon/react";
import { useState } from "react";
import type { FormEvent } from "react";
import { AvisoError } from "../comun/AvisoError";

interface Props {
  // POST /v1/sesion/contrasena. Si la API rechaza, lanza ErrorDeApi con su `detalle`.
  alCambiar: (actual: string, nueva: string) => Promise<void>;
}

// Cambio obligatorio de contraseña (`debe_cambiar_clave`): la cuenta lo exige antes de usar nada mas. La regla de
// la contraseña nueva (largo, etc.) la pone la API; aqui solo se comprueba que este escrita y bien confirmada.
export function CambiarContrasena({ alCambiar }: Props) {
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [intentado, setIntentado] = useState(false);

  const noCoincide = confirmacion !== "" && confirmacion !== nueva;

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setIntentado(true);
    if (!actual || !nueva || confirmacion !== nueva) return;
    setEnviando(true);
    setError(null);
    try {
      await alCambiar(actual, nueva);
    } catch (e) {
      setError(e);
      setEnviando(false);
    }
  }

  return (
    <main className="silice-entrada">
      <h1 className="cds--type-heading-03">Cambie su contraseña</h1>
      <p className="silice-entrada__texto cds--type-body-compact-01">
        Su cuenta tiene una contraseña provisional. Elija una nueva antes de seguir.
      </p>
      <Form className="silice-entrada__formulario" onSubmit={enviar} noValidate>
        <PasswordInput
          id="clave-actual"
          labelText="Contraseña actual"
          autoComplete="current-password"
          value={actual}
          onChange={(e) => setActual(e.target.value)}
          invalid={intentado && !actual}
          invalidText="Escriba su contraseña actual."
        />
        <PasswordInput
          id="clave-nueva"
          labelText="Contraseña nueva"
          autoComplete="new-password"
          value={nueva}
          onChange={(e) => setNueva(e.target.value)}
          invalid={intentado && !nueva}
          invalidText="Escriba la contraseña nueva."
        />
        <PasswordInput
          id="clave-confirmacion"
          labelText="Confirme la contraseña nueva"
          autoComplete="new-password"
          value={confirmacion}
          onChange={(e) => setConfirmacion(e.target.value)}
          invalid={(intentado || confirmacion !== "") && noCoincide}
          invalidText="Las contraseñas nuevas no coinciden."
        />
        <AvisoError error={error} titulo="No se pudo cambiar la contraseña" />
        <Button type="submit" disabled={enviando}>
          {enviando ? "Cambiando…" : "Cambiar contraseña"}
        </Button>
      </Form>
    </main>
  );
}
