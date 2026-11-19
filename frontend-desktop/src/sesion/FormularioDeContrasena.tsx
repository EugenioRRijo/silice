import { Button, Form } from "@carbon/react";
import { useState } from "react";
import type { FormEvent } from "react";
import { AvisoError } from "../comun/AvisoError";
import { PasswordInput } from "../comun/carbonEs";

interface Props {
  // POST /v1/sesion/contrasena. Si la API rechaza, lanza ErrorDeApi con su `detalle`.
  alCambiar: (actual: string, nueva: string) => Promise<void>;
  // Con esta función el formulario sigue en pantalla tras cambiarla: se vacía y se avisa (la Cuenta). Sin ella, quien lo
  // monta lo cambia por otra pantalla al cambiar la sesión (el cambio obligatorio) y el botón queda en «Cambiando…».
  alCambiado?: () => void;
  // Se llama al escribir en cualquier campo (la Cuenta quita el «Contraseña cambiada» de la vez anterior).
  alEscribir?: () => void;
}

// Los tres campos de un cambio de contraseña: la actual, la nueva y su confirmación. La regla de la contraseña nueva
// (largo, etc.) la pone la API; aquí solo se comprueba que esté escrita y bien confirmada.
export function FormularioDeContrasena({ alCambiar, alCambiado, alEscribir }: Props) {
  const [actual, setActual] = useState("");
  const [nueva, setNueva] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [intentado, setIntentado] = useState(false);

  const noCoincide = confirmacion !== "" && confirmacion !== nueva;
  const sinConfirmar = intentado && confirmacion === "";
  const escribir = (poner: (valor: string) => void) => (valor: string) => {
    poner(valor);
    alEscribir?.();
  };

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
      return;
    }
    if (alCambiado === undefined) return;
    setActual("");
    setNueva("");
    setConfirmacion("");
    setIntentado(false);
    setEnviando(false);
    alCambiado();
  }

  return (
    <Form className="silice-entrada__formulario" onSubmit={enviar} noValidate>
      <PasswordInput
        id="clave-actual"
        labelText="Contraseña actual"
        autoComplete="current-password"
        value={actual}
        onChange={(e) => escribir(setActual)(e.target.value)}
        invalid={intentado && !actual}
        invalidText="Escriba su contraseña actual."
      />
      <PasswordInput
        id="clave-nueva"
        labelText="Contraseña nueva"
        autoComplete="new-password"
        value={nueva}
        onChange={(e) => escribir(setNueva)(e.target.value)}
        invalid={intentado && !nueva}
        invalidText="Escriba la contraseña nueva."
      />
      <PasswordInput
        id="clave-confirmacion"
        labelText="Confirme la contraseña nueva"
        autoComplete="new-password"
        value={confirmacion}
        onChange={(e) => escribir(setConfirmacion)(e.target.value)}
        invalid={sinConfirmar || ((intentado || confirmacion !== "") && noCoincide)}
        invalidText={sinConfirmar ? "Confirme la contraseña nueva." : "Las contraseñas nuevas no coinciden."}
      />
      <AvisoError error={error} titulo="No se pudo cambiar la contraseña" />
      <Button type="submit" disabled={enviando}>
        {enviando ? "Cambiando…" : "Cambiar contraseña"}
      </Button>
    </Form>
  );
}
