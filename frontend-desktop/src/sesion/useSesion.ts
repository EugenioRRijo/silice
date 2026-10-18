import { useCallback, useEffect, useState } from "react";
import { ErrorDeApi, fijarCsrf, pedir } from "../api/cliente";
import type { SesionRespuesta } from "../api/tipos";

export type EstadoDeSesion =
  | { tipo: "cargando" }
  | { tipo: "sin_sesion"; expirada: boolean }
  | { tipo: "activa"; sesion: SesionRespuesta };

// La sesion vive en una cookie HttpOnly que pone la API. Aqui solo se guarda en memoria lo que la API devuelve
// (nombre, roles y el token anti-CSRF); nada va a localStorage ni a sessionStorage (RT-9).
export function useSesion() {
  const [estado, setEstado] = useState<EstadoDeSesion>({ tipo: "cargando" });

  useEffect(() => {
    let vigente = true;
    pedir<SesionRespuesta>("/v1/sesion")
      .then((sesion) => {
        if (!vigente) return;
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
    const sesion = await pedir<SesionRespuesta>("/v1/sesion", { metodo: "POST", cuerpo: { login, contrasena } });
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

  return { estado, entrar, salir, expirar };
}
