import { ErrorDeApi, pedir } from "../api/cliente";
import type { ModuloId } from "./rutas";

// Lo que la cuenta recuerda de la interfaz (MOD-0): el ultimo modulo y si quiere el sidebar fijado. Un 401 es la sesion
// vencida; cualquier otro error se calla: lo peor es entrar la proxima vez en otro modulo o con el sidebar oculto, y eso
// no merece interrumpir a la persona.
export async function guardarPreferencias(
  cambio: { modulo?: ModuloId; sidebar_fijado?: boolean },
  alExpirar: () => void,
): Promise<void> {
  try {
    await pedir("/v1/sesion/preferencias", { metodo: "PUT", cuerpo: cambio });
  } catch (e) {
    if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
  }
}
