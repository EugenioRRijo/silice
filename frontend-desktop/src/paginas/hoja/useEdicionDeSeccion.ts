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
// comportamiento que `useEdicionDelEspacio` (3c-1) para un estado `E` cualquiera.
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
  const mandar = useCallback(async (construir: (rev: number, estado: E) => Peticion, repetir: boolean): Promise<Resumen | null> => {
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
          setError(null);
          actuales.current.alAceptar(respuesta.resumen);
          actuales.current.alRelectura();
        } while (m.volver);
      } catch (e) {
        m.volver = false;
        aceptado = null;
        if (e instanceof ErrorDeApi && e.estado === 401) {
          actuales.current.alExpirar();
        } else if (esBorradorAusente(e)) {
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
        setEnvio(m.temporizador !== null ? "pendiente" : "quieto");
      }
      return aceptado;
    })();
    m.envioEnCurso = envio;
    return envio;
  }, []);

  const enviarEdicion = useCallback(() => mandar((rev, e) => actuales.current.peticion(rev, e), true), [mandar]);

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

  // Una acción que no espera la pausa (por ejemplo «Crear plan secuencial»). Con una petición en vuelo no se repite.
  const accionar = useCallback((peticion: (rev: number) => Peticion) => mandar((rev) => peticion(rev), false), [mandar]);

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

  // Lo último que aceptó el servidor (Esc devuelve un campo a eso).
  const aceptado = useCallback((): E => motor.current.aceptado, []);

  return { estado, envio, error, cambiar, accionar, accionarEnOrden, recargar, aceptado };
}
