import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { esperarEnvios } from "./envioPendiente";
import {
  cambiosDeRespuesta,
  clasificarErrorDeGuardado,
  cuerpoDeGuardado,
  rutaDeCambios,
  rutaDeGuardar,
} from "./logicaGuardar";
import type { CambioDeVersion, ErrorDeGuardado, GuardadoRespuesta } from "./logicaGuardar";

// null: se está leyendo; «error»: no se pudo leer.
export type CambiosDelModal = CambioDeVersion[] | null | "error";

interface Opciones {
  // El borrador abierto (null si todavía no hay uno), su `rev` según la página y el proyecto.
  id: string | null;
  rev: number;
  proyecto: string;
  alExpirar: () => void;
  // El servidor guardó la versión: la página abre la nueva. No debe lanzar.
  alGuardada: (respuesta: GuardadoRespuesta) => Promise<void>;
}

// El estado del modal «Guardar versión»: si está abierto, la fuente escrita (que sobrevive a un cierre o a un error), la lista de
// cambios (E9) y el guardado (S1). Hay una sola petición de guardado en vuelo a la vez.
export function useGuardado({ id, rev, proyecto, alExpirar, alGuardada }: Opciones) {
  const [abierto, setAbierto] = useState(false);
  const [escrita, setEscrita] = useState<{ proyecto: string; texto: string }>({ proyecto, texto: "" });
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState<ErrorDeGuardado | null>(null);
  const [leidos, setLeidos] = useState<{ clave: string; cambios: CambiosDelModal } | null>(null);
  const fuente = escrita.proyecto === proyecto ? escrita.texto : "";
  const enVuelo = useRef(false);
  const actuales = useRef({ id, rev, fuente });
  useEffect(() => {
    actuales.current = { id, rev, fuente };
  });

  const visible = abierto && id !== null;
  // La lista de cambios se vuelve a leer si el borrador cambia mientras el modal está abierto (por ejemplo una edición que
  // estaba en la pausa de 400 ms cuando se abrió).
  const clave = visible ? JSON.stringify([id, rev]) : null;
  useEffect(() => {
    if (clave === null || id === null) return;
    let vigente = true;
    pedir<unknown>(rutaDeCambios(id)).then(
      (r) => {
        if (vigente) setLeidos({ clave, cambios: cambiosDeRespuesta(r) ?? "error" });
      },
      (e: unknown) => {
        if (!vigente) return;
        if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
        setLeidos({ clave, cambios: "error" });
      },
    );
    return () => {
      vigente = false;
    };
  }, [clave, id, alExpirar]);
  // Mientras llega la lista nueva se sigue mostrando la anterior (no parpadea).
  const cambios: CambiosDelModal = leidos === null ? null : leidos.cambios;

  const abrir = useCallback(() => setAbierto(true), []);
  const cerrar = useCallback(() => {
    setAbierto(false);
    setError(null);
    setLeidos(null);
  }, []);
  const escribir = useCallback((texto: string) => setEscrita({ proyecto, texto }), [proyecto]);
  const limpiarError = useCallback(() => setError(null), []);

  const guardar = useCallback(
    async (confirmarVersionMasNueva = false) => {
      const { id: borrador } = actuales.current;
      if (borrador === null || enVuelo.current) return;
      enVuelo.current = true;
      setEnviando(true);
      setError(null);
      let respuesta: GuardadoRespuesta;
      try {
        // Lo que salió al desmontar una pestaña (la pausa de 400 ms no llegó a cumplirse) debe aceptarse antes de guardar.
        await esperarEnvios(borrador);
        const { rev: revVigente, fuente: texto } = actuales.current;
        respuesta = await pedir<GuardadoRespuesta>(rutaDeGuardar(borrador), {
          metodo: "POST",
          cuerpo: cuerpoDeGuardado(revVigente, texto, confirmarVersionMasNueva),
        });
      } catch (e) {
        if (e instanceof ErrorDeApi && e.estado === 401) alExpirar();
        setError(clasificarErrorDeGuardado(e));
        enVuelo.current = false;
        setEnviando(false);
        return;
      }
      enVuelo.current = false;
      setEnviando(false);
      setAbierto(false);
      setLeidos(null);
      setEscrita({ proyecto, texto: "" });
      await alGuardada(respuesta);
    },
    [alExpirar, alGuardada, proyecto],
  );

  return { abierto: visible, abrir, cerrar, fuente, escribir, enviando, error, limpiarError, cambios, guardar };
}
