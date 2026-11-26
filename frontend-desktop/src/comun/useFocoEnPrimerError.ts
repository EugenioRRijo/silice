import { useCallback, useEffect, useRef, useState } from "react";
import type { RefObject } from "react";

export interface CampoConPosibleError {
  error: string | null | undefined;
  ref: RefObject<HTMLElement | null>;
}

// Lleva el foco al primer campo con error una vez pintado su estado inválido o montado su aviso en el DOM (generaliza
// el patrón de `paginas/indices/SeriesViales.tsx`).
export function useFocoEnPrimerError(): (campos: ReadonlyArray<CampoConPosibleError>) => boolean {
  const objetivo = useRef<RefObject<HTMLElement | null> | null>(null);
  const [intento, setIntento] = useState(0);

  useEffect(() => {
    if (intento === 0) return;
    objetivo.current?.current?.focus();
  }, [intento]);

  return useCallback((campos: ReadonlyArray<CampoConPosibleError>): boolean => {
    const primero = campos.find((campo) => typeof campo.error === "string" && campo.error !== "");
    if (primero === undefined) return false;
    objetivo.current = primero.ref;
    setIntento((antes) => antes + 1);
    return true;
  }, []);
}
