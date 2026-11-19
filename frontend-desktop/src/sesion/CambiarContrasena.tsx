import { FormularioDeContrasena } from "./FormularioDeContrasena";

interface Props {
  // POST /v1/sesion/contrasena. Si la API rechaza, lanza ErrorDeApi con su `detalle`.
  alCambiar: (actual: string, nueva: string) => Promise<void>;
}

// Cambio obligatorio de contraseña (`debe_cambiar_clave`): la cuenta lo exige antes de usar nada mas. La regla de
// la contraseña nueva (largo, etc.) la pone la API; los campos son los de FormularioDeContrasena.
export function CambiarContrasena({ alCambiar }: Props) {
  return (
    <main className="silice-entrada">
      <h1 className="cds--type-heading-03">Cambie su contraseña</h1>
      <p className="silice-entrada__texto cds--type-body-compact-01">
        Su cuenta tiene una contraseña provisional. Elija una nueva antes de seguir.
      </p>
      <FormularioDeContrasena alCambiar={alCambiar} />
    </main>
  );
}
