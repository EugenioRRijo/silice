import { useCallback, useEffect, useState } from "react";
import { ErrorDeApi, fijarCsrf, pedir } from "../api/cliente";
import { invalidarRecursos } from "../comun/recurso";
import type { SesionRespuesta } from "../api/tipos";
import type { CuerpoDeReclamo } from "../bienvenida/FormularioDeReclamo";

export type EstadoDeSesion =
  | { tipo: "cargando" }
  | { tipo: "sin_sesion"; expirada: boolean }
  | { tipo: "activa"; sesion: SesionRespuesta };

type SesionBruta = Partial<SesionRespuesta> & Pick<SesionRespuesta, "login" | "nombre" | "roles" | "csrf">;

// La sesion termino en este navegador (la persona salio o el servidor la dio por vencida): ya no hay con que pedirle nada. Lo
// que las pantallas pedirian al irse (descartar el borrador de la Hoja, `DELETE /v1/hoja/borradores/{id}`) volveria con un
// 401 que no dice nada, y no hace falta: al cerrar la sesion el servidor ya descarta los borradores sin cambios
// (api/caso_web.py). La bandera vive fuera del estado de React porque la lee el desmontaje de las pantallas, que ocurre
// despues de que el estado cambia; se baja al abrir una sesion. Solo en memoria (RT-9).
let terminada = false;
const oyentesDeApertura = new Set<(sesion: SesionRespuesta) => void>();

export function sesionTerminada(): boolean {
  return terminada;
}

// Una API anterior a la ola 0a no trae estos campos: sin ellos, nadie debe cambiar clave, no hay acciones (el
// menu queda vacio) y no hay modo entrega. Sin los de MOD-0, no hay eleccion recordada y las preferencias son las
// de omision (ningun modulo, sidebar oculto).
function normalizar(bruta: SesionBruta): SesionRespuesta {
  return {
    ...bruta,
    debe_cambiar_clave: bruta.debe_cambiar_clave === true,
    acciones: Array.isArray(bruta.acciones) ? bruta.acciones : [],
    modo_entrega: bruta.modo_entrega === true,
    eleccion: bruta.eleccion ?? null,
    preferencias: bruta.preferencias ?? { modulo: null, sidebar_fijado: false },
  };
}

// Puerta única en el cliente para activar una sesión devuelta por la API (`GET/POST /v1/sesion`, reclamo del primer
// arranque, cambio de contraseña y canje de código en `POST /v1/solicitudes/canjear`): normaliza el cuerpo, guarda el
// token anti-CSRF en memoria, baja la marca de sesión terminada y actualiza las instancias montadas de `useSesion`.
function activarSesion(bruta: SesionBruta): SesionRespuesta {
  const sesion = normalizar(bruta);
  fijarCsrf(sesion.csrf);
  terminada = false;
  for (const oyente of [...oyentesDeApertura]) {
    oyente(sesion);
  }
  return sesion;
}

export async function canjearCodigo(login: string, contrasena: string, codigo: string): Promise<void> {
  activarSesion(
    await pedir<SesionRespuesta>("/v1/solicitudes/canjear", {
      metodo: "POST",
      cuerpo: { login, contrasena, codigo },
    }),
  );
}

// La sesion vive en una cookie HttpOnly que pone la API. Aqui solo se guarda en memoria lo que la API devuelve
// (nombre, roles, acciones y el token anti-CSRF); nada va a localStorage ni a sessionStorage (RT-9).
export function useSesion() {
  const [estado, setEstado] = useState<EstadoDeSesion>({ tipo: "cargando" });

  useEffect(() => {
    const alAbrir = (sesion: SesionRespuesta) => {
      setEstado({ tipo: "activa", sesion });
    };
    oyentesDeApertura.add(alAbrir);
    return () => {
      oyentesDeApertura.delete(alAbrir);
    };
  }, []);

  useEffect(() => {
    let vigente = true;
    pedir<SesionRespuesta>("/v1/sesion")
      .then((bruta) => {
        if (!vigente) return;
        const sesion = activarSesion(bruta);
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
    const sesion = activarSesion(
      await pedir<SesionRespuesta>("/v1/sesion", { metodo: "POST", cuerpo: { login, contrasena } }),
    );
    setEstado({ tipo: "activa", sesion });
  }, []);

  const canjear = useCallback(async (login: string, contrasena: string, codigo: string) => {
    await canjearCodigo(login, contrasena, codigo);
  }, []);

  // Primer arranque y restablecimiento (BCP-4): el código de un solo uso crea (o recupera) la cuenta administradora y la API
  // abre la sesión con el mismo cuerpo que POST /v1/sesion (201). El cuerpo no se guarda aquí: pasa de largo a la API.
  const reclamar = useCallback(async (cuerpo: CuerpoDeReclamo) => {
    const sesion = activarSesion(
      await pedir<SesionRespuesta>("/v1/primer-arranque/reclamo", { metodo: "POST", cuerpo }),
    );
    setEstado({ tipo: "activa", sesion });
  }, []);

  // Cambio obligatorio: la API acepta la clave nueva y la persona entra con la sesion ya completa, que se vuelve
  // a leer (acciones, modo entrega y un token anti-CSRF nuevo si la API lo rota).
  // La respuesta del POST es la ficha nueva (mismo cuerpo que `POST /v1/sesion`, con otro token anti-CSRF): se usa tal cual. Una
  // API que no la trae se relee con `GET /v1/sesion`. Un 401 es que la sesión ya no valía (venció o se cerró en otra pestaña).
  const cambiarContrasena = useCallback(async (actual: string, nueva: string) => {
    let respuesta: unknown;
    try {
      respuesta = await pedir<unknown>("/v1/sesion/contrasena", { metodo: "POST", cuerpo: { actual, nueva } });
    } catch (error) {
      if (error instanceof ErrorDeApi && error.estado === 401) {
        fijarCsrf(null);
        terminada = true;
        setEstado({ tipo: "sin_sesion", expirada: true });
      }
      throw error;
    }
    const trae = (r: unknown): r is SesionBruta =>
      typeof r === "object" && r !== null && "login" in r && "csrf" in r;
    const sesion = activarSesion(trae(respuesta) ? respuesta : await pedir<SesionRespuesta>("/v1/sesion"));
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
    // Los datos en caché son de la cuenta que sale: la siguiente no debe verlos.
    invalidarRecursos("");
    // Antes de cambiar el estado: el desmontaje de las pantallas que sigue ya lo lee.
    terminada = true;
    setEstado({ tipo: "sin_sesion", expirada: false });
  }, []);

  // El servidor dijo 401 en medio del trabajo: la sesion vencio por inactividad.
  const expirar = useCallback(() => {
    fijarCsrf(null);
    terminada = true;
    setEstado({ tipo: "sin_sesion", expirada: true });
  }, []);

  return { estado, entrar, canjear, reclamar, cambiarContrasena, salir, expirar };
}
