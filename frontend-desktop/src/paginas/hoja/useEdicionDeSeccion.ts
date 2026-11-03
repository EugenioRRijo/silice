import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { mensajeDeError } from "../../comun/errores";
import { PAUSA_DE_EDICION_MS, esBorradorAusente, mensajeDeRechazo } from "./logica";
import type { RespuestaDeEdicion, Resumen } from "./logica";
import { registrarEnvio } from "./envioPendiente";
import { claseDeConflicto } from "./logicaSecciones";

export type EnvioDeSeccion = "quieto" | "pendiente" | "enviando";

export interface ErrorDeSeccion<U> {
  // «rechazo»: el servidor no aceptó el texto (422); «conflicto»: el `rev` es viejo (409), se recarga; «perdido»: el caso
  // cambió o el borrador ya se guardó (409), solo se abre de nuevo; «otro»: cualquier otro fallo (incluido un 409 que no
  // bloquea, como «ya tiene plan»).
  tipo: "rechazo" | "conflicto" | "perdido" | "otro";
  mensaje: string;
  ubicacion: U | null;
}

export interface Peticion {
  ruta: string;
  metodo: "PUT" | "POST";
  cuerpo: object;
  // Lo que la clásica agrega tras el error de esta petición; si falta, el de la sección. "" = el `detalle` solo.
  frase?: string;
}

interface Opciones<E, U> {
  // El borrador que se edita: lo que sale al irse de la pestaña se anota a su nombre (ver `envioPendiente`).
  borrador: string;
  // Lo que se edita al montar (las celdas como texto). Solo se lee la primera vez.
  inicial: E;
  // El `rev` con que está el borrador según la página (sube al aceptar una edición o recargarlo).
  rev: number;
  // La petición con que se manda `estado` tras la pausa.
  peticion: (rev: number, estado: E) => Peticion;
  // Dónde está el error de un 422 (fila, campo, partida...), o null si el mensaje no lo dice.
  ubicar: (detalle: string) => U | null;
  // Lo que la clásica agrega tras el error de esta sección.
  frase: string;
  // Vuelve a leer la vista de la sección y la siembra (tras un 409 por `rev`).
  leerFresca: () => Promise<E>;
  alAceptar: (resumen: Resumen) => void;
  // Pide volver a leer la vista de la pestaña tras una edición.
  alRelectura: () => void;
  // Vuelve a leer el borrador del servidor (su `rev` y su resumen).
  alRecargarBorrador: () => Promise<void>;
  alAusente: () => void;
  alExpirar: () => void;
}

// El motor de la edición de una sección (cantidades, parámetros, plan): guarda lo editable como texto, espera la pausa de
// 400 ms tras la última tecla, manda con el `rev` que vio (una sola petición en vuelo; lo escrito entre tanto sale en
// otra) y deja el error del servidor para mostrarlo. No guarda nada: solo edita el borrador del servidor. Es el mismo
// comportamiento de la edición del espacio (3c-1), que ya lo usa, para un estado `E` cualquiera.
export function useEdicionDeSeccion<E, U>(opciones: Opciones<E, U>) {
  const [estado, setEstado] = useState<E>(opciones.inicial);
  const [envio, setEnvio] = useState<EnvioDeSeccion>("quieto");
  const [error, setError] = useState<ErrorDeSeccion<U> | null>(null);

  // Lo que los manejadores de eventos y de temporizador necesitan ver al día (no se lee al pintar).
  const motor = useRef({
    estado,
    aceptado: estado,
    rev: opciones.rev,
    revDeLaPagina: opciones.rev,
    temporizador: null as ReturnType<typeof setTimeout> | null,
    enVuelo: false,
    volver: false,
    bloqueado: false,
    // Lo que se está mandando ahora (para esperarlo antes de una acción que no puede adelantarse).
    envioEnCurso: null as Promise<Resumen | null> | null,
  });
  // `enviarEdicion`, para mandar lo escrito mientras iba una acción (se fija en un efecto).
  const reenviar = useRef<((conservarError: boolean) => Promise<Resumen | null>) | null>(null);
  const actuales = useRef(opciones);

  useEffect(() => {
    // Solo cuando la página trae un `rev` nuevo (por ejemplo tras recargar): un render con el viejo no pisa el que acaba de contestar el servidor.
    if (motor.current.revDeLaPagina !== opciones.rev) {
      motor.current.revDeLaPagina = opciones.rev;
      motor.current.rev = opciones.rev;
    }
    actuales.current = opciones;
  });

  // Manda una petición y devuelve el resumen que contestó el servidor, o null si no se aceptó (o ya había una en vuelo).
  // `conservarError`: el reenvío de lo escrito tras una acción fallida no borra, al aceptarse, el aviso de esa acción.
  const mandar = useCallback(async (construir: (rev: number, estado: E) => Peticion, repetir: boolean, conservarError = false): Promise<Resumen | null> => {
    const m = motor.current;
    if (m.bloqueado) return null;
    if (m.enVuelo) {
      if (repetir) m.volver = true;
      return null;
    }
    m.enVuelo = true;
    setEnvio("enviando");
    const envio = (async (): Promise<Resumen | null> => {
      let frase = actuales.current.frase;
      let aceptado: Resumen | null = null;
      // La acción falló (su aviso se conserva) o la sesión o el borrador se perdieron (no se reenvía nada).
      let fallo = false;
      let perdido = false;
      try {
        do {
          m.volver = false;
          const enviado = m.estado;
          const peticion = construir(m.rev, enviado);
          frase = peticion.frase ?? actuales.current.frase;
          const respuesta = await pedir<RespuestaDeEdicion>(peticion.ruta, { metodo: peticion.metodo, cuerpo: peticion.cuerpo });
          m.rev = respuesta.rev;
          m.aceptado = enviado;
          aceptado = respuesta.resumen;
          if (!conservarError) setError(null);
          actuales.current.alAceptar(respuesta.resumen);
          actuales.current.alRelectura();
          // Solo la edición se repite con lo último escrito; una acción (quitar, usar un insumo) no se repite.
        } while (repetir && m.volver);
      } catch (e) {
        if (repetir) m.volver = false;
        fallo = true;
        // Si una vuelta anterior ya se aceptó, `aceptado` es lo último que el servidor tiene; si no, sigue en null.
        if (e instanceof ErrorDeApi && e.estado === 401) {
          perdido = true;
          actuales.current.alExpirar();
        } else if (esBorradorAusente(e)) {
          perdido = true;
          actuales.current.alAusente();
        } else if (e instanceof ErrorDeApi && e.estado === 409) {
          const clase = claseDeConflicto(e.detalle);
          if (clase === "otro") {
            // Un conflicto de contenido (por ejemplo «ya tiene plan»): no bloquea; se vuelve a leer lo que hay.
            setError({ tipo: "otro", mensaje: e.detalle, ubicacion: null });
            actuales.current.alRelectura();
          } else {
            m.bloqueado = true; // hasta recargar (o abrir de nuevo) no se manda más
            setError({ tipo: clase === "rev" ? "conflicto" : "perdido", mensaje: e.detalle, ubicacion: null });
          }
        } else if (e instanceof ErrorDeApi && e.estado === 422) {
          setError({
            tipo: "rechazo",
            mensaje: mensajeDeRechazo(e.detalle, frase),
            ubicacion: actuales.current.ubicar(e.detalle),
          });
        } else {
          setError({ tipo: "otro", mensaje: mensajeDeError(e), ubicacion: null });
        }
      } finally {
        m.enVuelo = false;
        // Lo escrito mientras iba una acción sale ahora, con el `rev` que ella dejó; tras un 401 o sin borrador, no.
        const pendiente = !repetir && m.volver && !perdido;
        if (!repetir) m.volver = false;
        setEnvio(m.temporizador !== null ? "pendiente" : "quieto");
        if (pendiente) void reenviar.current?.(fallo);
      }
      return aceptado;
    })();
    m.envioEnCurso = envio;
    return envio;
  }, []);

  const enviarEdicion = useCallback(() => mandar((rev, e) => actuales.current.peticion(rev, e), true), [mandar]);
  useEffect(() => {
    reenviar.current = (conservarError) => mandar((rev, e) => actuales.current.peticion(rev, e), true, conservarError);
  }, [mandar]);

  // Cambia lo editable y programa el envío tras la pausa. `cambio` recibe lo último (no lo último pintado).
  const cambiar = useCallback(
    (cambio: (previo: E) => E) => {
      const m = motor.current;
      m.estado = cambio(m.estado);
      setEstado(m.estado);
      if (m.bloqueado) return;
      if (m.temporizador !== null) clearTimeout(m.temporizador);
      setEnvio((actual) => (actual === "enviando" ? actual : "pendiente"));
      m.temporizador = setTimeout(() => {
        m.temporizador = null;
        void enviarEdicion();
      }, PAUSA_DE_EDICION_MS);
    },
    [enviarEdicion],
  );

  // Una acción que no puede adelantarse a lo escrito (por ejemplo «Usar este insumo»): primero sale la edición que espera la
  // pausa, se espera a la que va en vuelo y solo entonces se manda la acción con el `rev` que contestó el servidor.
  const accionarEnOrden = useCallback(
    async (peticion: (rev: number) => Peticion): Promise<Resumen | null> => {
      const m = motor.current;
      if (m.temporizador !== null) {
        clearTimeout(m.temporizador);
        m.temporizador = null;
        await enviarEdicion();
      }
      while (m.enVuelo && m.envioEnCurso !== null) await m.envioEnCurso;
      return mandar((rev) => peticion(rev), false);
    },
    [mandar, enviarEdicion],
  );

  // Para una acción con su propio manejo de errores (agregar una partida desde su diálogo): manda ya la edición que espera
  // la pausa, espera la que va en vuelo y devuelve el `rev` con que quedó el borrador. Quien llama manda su petición con
  // ese `rev` y pasa el resumen nuevo a la página (`alAceptar`), que trae el `rev` nuevo a este motor.
  const esperarEnvios = useCallback(async (): Promise<number> => {
    const m = motor.current;
    if (m.temporizador !== null) {
      clearTimeout(m.temporizador);
      m.temporizador = null;
      await enviarEdicion();
    }
    while (m.enVuelo && m.envioEnCurso !== null) await m.envioEnCurso;
    return m.rev;
  }, [enviarEdicion]);

  // Al irse de la pestaña con una edición esperando la pausa, se manda en seguida para no perderla.
  useEffect(() => {
    const m = motor.current;
    return () => {
      if (m.temporizador !== null) {
        clearTimeout(m.temporizador);
        m.temporizador = null;
        void enviarEdicion();
      }
      // Lo que va en vuelo (o acaba de salir) se anota para que quien descarte el borrador espere a que termine.
      if (m.enVuelo && m.envioEnCurso !== null) registrarEnvio(actuales.current.borrador, m.envioEnCurso);
    };
  }, [enviarEdicion]);

  // Tras un 409 por `rev`: se vuelve a leer el borrador y la vista, y se vuelve a sembrar lo que se ve.
  const recargar = useCallback(async () => {
    const m = motor.current;
    try {
      await actuales.current.alRecargarBorrador();
      const fresca = await actuales.current.leerFresca();
      if (m.temporizador !== null) clearTimeout(m.temporizador);
      m.temporizador = null;
      m.estado = fresca;
      m.aceptado = fresca;
      m.bloqueado = false;
      m.volver = false;
      setEstado(fresca);
      setError(null);
      setEnvio("quieto");
      actuales.current.alRelectura();
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) actuales.current.alExpirar();
      else if (esBorradorAusente(e)) actuales.current.alAusente();
      else setError({ tipo: "otro", mensaje: mensajeDeError(e), ubicacion: null });
    }
  }, []);

  // La vista cambió de forma (se agregó o se quitó un renglón): se vuelve a sembrar sin mandar nada y sin borrar el error.
  // `cambio` recibe lo escrito y lo aceptado y decide qué se conserva (lo tocado y no aceptado). Lo que espera la pausa
  // sale igual, ya con la siembra nueva.
  const resembrar = useCallback((cambio: (escrito: E, yaAceptado: E) => { estado: E; aceptado: E }) => {
    const m = motor.current;
    const nuevo = cambio(m.estado, m.aceptado);
    m.estado = nuevo.estado;
    m.aceptado = nuevo.aceptado;
    setEstado(nuevo.estado);
  }, []);

  // Lo último que aceptó el servidor (Esc devuelve un campo a eso).
  const aceptado = useCallback((): E => motor.current.aceptado, []);

  return { estado, envio, error, cambiar, accionarEnOrden, esperarEnvios, resembrar, recargar, aceptado };
}
