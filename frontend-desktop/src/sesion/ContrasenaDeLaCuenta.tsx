import { useState } from "react";
import { useAplicacion } from "../shell/contexto";
import { FormularioDeContrasena } from "./FormularioDeContrasena";

const SIN_CAMBIO = () => Promise.reject(new Error("Aquí no se puede cambiar la contraseña."));

// «Contraseña» en la Cuenta: la persona cambia la suya cuando quiere, no solo cuando es provisional. La API cierra todas
// las sesiones de la cuenta y abre otra (`POST /v1/sesion/contrasena`): se dice antes de confirmar, y la persona sigue en
// este navegador con la sesión nueva (`cambiarContrasena` de la sesión la relee). El título lo pone la Cuenta.
export function ContrasenaDeLaCuenta() {
  const { cambiarContrasena = SIN_CAMBIO } = useAplicacion();
  const [cambiada, setCambiada] = useState(false);
  return (
    <div className="silice-cuenta-preferencias">
      <section aria-labelledby="clave-titulo" className="silice-cuenta-preferencias__bloque">
        <h2 id="clave-titulo" className="cds--type-heading-compact-02">
          Cambiar mi contraseña
        </h2>
        <p className="cds--type-body-compact-01">
          Al cambiarla se cierran las sesiones de su cuenta abiertas en otros navegadores o pestañas. En este seguirá con la sesión abierta.
        </p>
        <FormularioDeContrasena alCambiar={cambiarContrasena} alCambiado={() => setCambiada(true)} alEscribir={() => setCambiada(false)} />
        <p role="status" className="cds--type-body-compact-01">
          {cambiada ? "Contraseña cambiada." : ""}
        </p>
      </section>
    </div>
  );
}
