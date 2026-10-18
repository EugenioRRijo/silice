import { useCallback, useEffect, useState } from "react";
import { ErrorDeApi, fijarCsrf, pedir } from "../api/cliente";
import type { SesionRespuesta } from "../api/tipos";

export type EstadoDeSesion =
  | { tipo: "cargando" }
  | { tipo: "sin_sesion"; expirada: boolean }
  | { tipo: "activa"; sesion: SesionRespuesta };

// Una API anterior a la ola 0a no trae estos campos: sin ellos, nadie debe cambiar clave, no hay acciones (el
// menu queda vacio) y no hay modo entrega.
function normalizar(bruta: Partial<SesionRespuesta> & Pick<SesionRespuesta, "login" | "nombre" | "roles" | "csrf">): SesionRespuesta {
  return {
    ...bruta,
    debe_cambiar_clave: bruta.debe_cambiar_clave === true,
    acciones: Array.isArray(bruta.acciones) ? bruta.acciones : [],
    modo_entrega: bruta.modo_entrega === true,
  };
}

// La sesion vive en una cookie HttpOnly que pone la API. Aqui solo se guarda en memoria lo que la API devuelve
// (nombre, roles, acciones y el token anti-CSRF); nada va a localStorage ni a sessionStorage (RT-9).
export function useSesion() {
  const [estado, setEstado] = useState<EstadoDeSesion>({ tipo: "cargando" });

  useEffect(() => {
    let vigente = true;
    pedir<SesionRespuesta>("/v1/sesion")
      .then((bruta) => {
        if (!vigente) return;
        const sesion = normalizar(bruta);
        fijarCsrf(sesion.csrf);
        setEstado({ tipo: "activa", sesion });
      })
      .catch(() => {
        if (vigente) setEstado({ tipo: "sin_sesion", expirada: false });
      });
    return () => {
      vigente = false;
    };
  }, []);

  const entrar = useCallback(async (login: string, contrasena: string) => {
    const sesion = normalizar(await pedir<SesionRespuesta>("/v1/sesion", { metodo: "POST", cuerpo: { login, contrasena } }));
    fijarCsrf(sesion.csrf);
    setEstado({ tipo: "activa", sesion });
  }, []);

  // Cambio obligatorio: la API acepta la clave nueva y la persona entra con la sesion ya completa, que se vuelve
  // a leer (acciones, modo entrega y un token anti-CSRF nuevo si la API lo rota).
  const cambiarContrasena = useCallback(async (actual: string, nueva: string) => {
    await pedir("/v1/sesion/contrasena", { metodo: "POST", cuerpo: { actual, nueva } });
    const sesion = normalizar(await pedir<SesionRespuesta>("/v1/sesion"));
    fijarCsrf(sesion.csrf);
    setEstado({ tipo: "activa", sesion });
  }, []);

  const salir = useCallback(async () => {
    try {
      await pedir("/v1/sesion", { metodo: "DELETE" });
    } catch (error) {
      // Si la sesion ya no existe en el servidor, igual hay que salir de la pantalla.
      if (!(error instanceof ErrorDeApi) || (error.estado !== 401 && error.estado !== 403)) throw error;
    }
    fijarCsrf(null);
    setEstado({ tipo: "sin_sesion", expirada: false });
  }, []);

  // El servidor dijo 401 en medio del trabajo: la sesion vencio por inactividad.
  const expirar = useCallback(() => {
    fijarCsrf(null);
    setEstado({ tipo: "sin_sesion", expirada: true });
  }, []);

  return { estado, entrar, cambiarContrasena, salir, expirar };
}
