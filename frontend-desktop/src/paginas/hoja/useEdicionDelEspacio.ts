import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { mensajeDeError } from "../../comun/errores";
import {
  PAUSA_DE_EDICION_MS,
  cuerpoDeEdicionDelEspacio,
  esBorradorAusente,
  mensajeDeRechazo,
  nuevaClaveDeFila,
  rutaDeEspacio,
  rutaDeVista,
  sembrarTablas,
  ubicarError,
} from "./logica";
import type { FilaEditable, RespuestaDeEdicion, Resumen, TablasEditables, UbicacionDeError, VistaEspacio } from "./logica";

export type EnvioDelEspacio = "quieto" | "pendiente" | "enviando";

export interface ErrorDeEdicion {
  // «rechazo»: el servidor no aceptó el texto (422); «conflicto»: el `rev` es viejo (409), se recarga; «perdido»: el caso cambió o el borrador ya se guardó (409), solo se abre de nuevo; «otro»: cualquier otro fallo.
  tipo: "rechazo" | "conflicto" | "perdido" | "otro";
  mensaje: string;
  ubicacion: UbicacionDeError | null;
}

interface Opciones {
  id: string;
  vista: VistaEspacio;
  // El `rev` con que está el borrador según la página (sube al aceptar una edición o recargarlo).
  rev: number;
  alAceptar: (resumen: Resumen) => void;
  // Pide volver a leer la vista del espacio (estado, derivadas y total) tras una edición.
  alRelectura: () => void;
  // Vuelve a leer el borrador del servidor (su `rev` y su resumen).
  alRecargarBorrador: () => Promise<void>;
  alAusente: () => void;
  alExpirar: () => void;
}

// El motor de la edición del espacio: guarda las cinco tablas como texto, espera la pausa de 400 ms tras la última
// tecla, manda la tabla completa con el `rev` que vio (una sola petición en vuelo; lo escrito entre tanto sale en otra)
// y deja el error del servidor (422 con el `detalle` de la clásica, 409 por `rev` viejo) para mostrarlo. No guarda nada:
// solo edita el borrador del servidor.
export function useEdicionDelEspacio({ id, vista, rev, alAceptar, alRelectura, alRecargarBorrador, alAusente, alExpirar }: Opciones) {
  const [tablas, setTablas] = useState<TablasEditables>(() => sembrarTablas(vista.tablas, vista.filas, nuevaClaveDeFila));
  const [envio, setEnvio] = useState<EnvioDelEspacio>("quieto");
  const [error, setError] = useState<ErrorDeEdicion | null>(null);

  // Lo que los manejadores de eventos y de temporizador necesitan ver al día (no se lee al pintar).
  const motor = useRef({
    tablas,
    aceptadas: tablas,
    rev,
    revDeLaPagina: rev,
    vista,
    temporizador: null as ReturnType<typeof setTimeout> | null,
    enVuelo: false,
    volver: false,
    bloqueado: false,
  });
  const llamadas = useRef({ alAceptar, alRelectura, alRecargarBorrador, alAusente, alExpirar });

  useEffect(() => {
    // Solo cuando la página trae un `rev` nuevo (por ejemplo tras recargar): un render con el viejo no pisa el que acaba de contestar el servidor.
    if (motor.current.revDeLaPagina !== rev) {
      motor.current.revDeLaPagina = rev;
      motor.current.rev = rev;
    }
    motor.current.vista = vista;
    llamadas.current = { alAceptar, alRelectura, alRecargarBorrador, alAusente, alExpirar };
  });

  const enviar = useCallback(async () => {
    const m = motor.current;
    if (m.bloqueado) return;
    if (m.enVuelo) {
      m.volver = true;
      return;
    }
    m.enVuelo = true;
    setEnvio("enviando");
    try {
      do {
        m.volver = false;
        const enviadas = m.tablas;
        const respuesta = await pedir<RespuestaDeEdicion>(rutaDeEspacio(id), {
          metodo: "PUT",
          cuerpo: cuerpoDeEdicionDelEspacio(m.rev, m.vista.tablas, enviadas),
        });
        m.rev = respuesta.rev;
        m.aceptadas = enviadas;
        setError(null);
        llamadas.current.alAceptar(respuesta.resumen);
        llamadas.current.alRelectura();
      } while (m.volver);
    } catch (e) {
      m.volver = false;
      if (e instanceof ErrorDeApi && e.estado === 401) {
        llamadas.current.alExpirar();
      } else if (esBorradorAusente(e)) {
        llamadas.current.alAusente();
      } else if (e instanceof ErrorDeApi && e.estado === 409) {
        m.bloqueado = true; // hasta recargar (o abrir de nuevo) no se manda más
        // Solo el 409 de `rev` viejo se arregla recargando; «el caso cambió» y «ya se guardó» también fallarían al recargar.
        setError({ tipo: e.detalle.startsWith("El borrador cambió") ? "conflicto" : "perdido", mensaje: e.detalle, ubicacion: null });
      } else if (e instanceof ErrorDeApi && e.estado === 422) {
        setError({ tipo: "rechazo", mensaje: mensajeDeRechazo(e.detalle), ubicacion: ubicarError(e.detalle, m.vista.tablas) });
      } else {
        setError({ tipo: "otro", mensaje: mensajeDeError(e), ubicacion: null });
      }
    } finally {
      m.enVuelo = false;
      setEnvio(m.temporizador !== null ? "pendiente" : "quieto");
    }
  }, [id]);

  const cambiarFilas = useCallback(
    (tabla: string, filas: FilaEditable[]) => {
      const m = motor.current;
      m.tablas = { ...m.tablas, [tabla]: filas };
      setTablas(m.tablas);
      if (m.bloqueado) return;
      if (m.temporizador !== null) clearTimeout(m.temporizador);
      setEnvio((actual) => (actual === "enviando" ? actual : "pendiente"));
      m.temporizador = setTimeout(() => {
        m.temporizador = null;
        void enviar();
      }, PAUSA_DE_EDICION_MS);
    },
    [enviar],
  );

  // Al irse de la pestaña con una edición esperando la pausa, se manda en seguida para no perderla.
  useEffect(() => {
    const m = motor.current;
    return () => {
      if (m.temporizador === null) return;
      clearTimeout(m.temporizador);
      m.temporizador = null;
      void enviar();
    };
  }, [enviar]);

  // Tras un 409: se vuelve a leer el borrador y las tablas del servidor, y se vuelve a sembrar lo que se ve.
  const recargar = useCallback(async () => {
    const m = motor.current;
    try {
      await llamadas.current.alRecargarBorrador();
      const fresca = await pedir<VistaEspacio>(rutaDeVista(id, "espacio"));
      const sembradas = sembrarTablas(fresca.tablas, fresca.filas, nuevaClaveDeFila);
      if (m.temporizador !== null) clearTimeout(m.temporizador);
      m.temporizador = null;
      m.tablas = sembradas;
      m.aceptadas = sembradas;
      m.vista = fresca;
      m.bloqueado = false;
      m.volver = false;
      setTablas(sembradas);
      setError(null);
      setEnvio("quieto");
      llamadas.current.alRelectura();
    } catch (e) {
      if (e instanceof ErrorDeApi && e.estado === 401) llamadas.current.alExpirar();
      else if (esBorradorAusente(e)) llamadas.current.alAusente();
      else setError({ tipo: "otro", mensaje: mensajeDeError(e), ubicacion: null });
    }
  }, [id]);

  const valorAceptado = useCallback(
    (tabla: string, filaClave: number, columna: string): string =>
      motor.current.aceptadas[tabla]?.find((f) => f.clave === filaClave)?.valores[columna] ?? "",
    [],
  );

  return { tablas, envio, error, cambiarFilas, recargar, valorAceptado };
}
