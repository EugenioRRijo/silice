import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { cuerpoDeLibro } from "./logicaDelLibro";
import type { AuditoriaDelLibro } from "./logicaDelLibro";

// Los estados de «Auditar un libro» (B2, ficha-b2 §1.8): vacío, con archivo elegido, auditando, con error y con resultado.
// Una unión discriminada: un estado ilegal (resultado sin archivo, por ejemplo) no se puede escribir.
export type EstadoDelLibro =
  | { fase: "vacio" }
  | { fase: "elegido"; archivo: File }
  | { fase: "cargando"; archivo: File }
  | { fase: "error"; archivo: File; error: unknown }
  | { fase: "listo"; archivo: File; fecha: string; auditoria: AuditoriaDelLibro };

export const RUTA_AUDITORIA = "/v1/libros/auditoria";

export interface AuditoriaEnCurso {
  estado: EstadoDelLibro;
  elegir: (archivo: File) => void;
  // Manda **una** auditoría. La réplica del libro (la hoja) no se pide aquí: solo si la persona pide verla.
  auditar: (archivo: File, fecha: string) => Promise<void>;
  reiniciar: () => void;
}

export function useAuditoriaDelLibro(alExpirar: () => void, alGuardar?: () => void): AuditoriaEnCurso {
  const [estado, setEstado] = useState<EstadoDelLibro>({ fase: "vacio" });
  // Para ignorar la respuesta de una auditoría que ya quedó atrás (otro libro, o «Auditar otro libro»).
  const turno = useRef(0);
  const alGuardarActual = useRef(alGuardar);
  useEffect(() => {
    alGuardarActual.current = alGuardar;
  });

  const elegir = useCallback((archivo: File) => {
    turno.current += 1;
    setEstado({ fase: "elegido", archivo });
  }, []);

  const reiniciar = useCallback(() => {
    turno.current += 1;
    setEstado({ fase: "vacio" });
  }, []);

  const auditar = useCallback(
    async (archivo: File, fecha: string) => {
      turno.current += 1;
      const mio = turno.current;
      setEstado({ fase: "cargando", archivo });
      try {
        const auditoria = await pedir<AuditoriaDelLibro>(RUTA_AUDITORIA, {
          metodo: "POST",
          cuerpo: cuerpoDeLibro(archivo, fecha),
        });
        if (mio === turno.current) {
          setEstado({ fase: "listo", archivo, fecha, auditoria });
          // Si el servidor avisó que no quedó en el historial (`aviso_historial`), no hace falta volver a pedirlo.
          if (!auditoria.aviso_historial) alGuardarActual.current?.();
        }
      } catch (error) {
        if (mio !== turno.current) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setEstado({ fase: "error", archivo, error });
      }
    },
    [alExpirar],
  );

  return { estado, elegir, auditar, reiniciar };
}
