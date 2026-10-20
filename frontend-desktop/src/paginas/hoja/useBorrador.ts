import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import type { BorradorAbierto, BorradorVivo } from "./logica";

// El borrador vivo de la hoja vive en el servidor (diseño §3.1): aquí solo se abre, se vuelve a leer y se descarta.
export type EstadoBorrador =
  | { estado: "inactivo" }
  | { estado: "abriendo" }
  | { estado: "listo"; borrador: BorradorAbierto }
  | { estado: "error"; error: unknown };

interface Abierto {
  id: string;
  cambios: number;
}

function descartar(id: string): void {
  // Sin esperar la respuesta: un borrador que quede por un fallo se va solo a las 8 horas.
  pedir(`/v1/hoja/borradores/${id}`, { metodo: "DELETE" }).catch(() => undefined);
}

// Abre `version` del `proyecto` (null = proyecto sin versiones; undefined = todavía no se sabe) y descarta el
// borrador al cambiar o al desmontar, salvo que tenga cambios sin guardar: esos se conservan para retomarlos (3c).
export function useBorrador(proyecto: string | null, version: string | null | undefined, alExpirar: () => void) {
  const [intento, setIntento] = useState(0);
  // El resultado lleva la clave de lo que se pidió: si ya no es la de ahora, lo visible es «abriendo».
  const [resultado, setResultado] = useState<{ clave: string; valor: EstadoBorrador } | null>(null);
  const abierto = useRef<Abierto | null>(null);
  const clave =
    proyecto === null || version === undefined ? null : JSON.stringify([proyecto, version, intento]);

  useEffect(() => {
    if (proyecto === null || version === undefined || clave === null) return;
    let vigente = true;
    pedir<BorradorAbierto>("/v1/hoja/borradores", { metodo: "POST", cuerpo: { proyecto, version } }).then(
      (borrador) => {
        if (!vigente) {
          descartar(borrador.id); // la persona ya se fue a otra versión: nadie lo va a usar
          return;
        }
        abierto.current = { id: borrador.id, cambios: borrador.resumen.cambios };
        setResultado({ clave, valor: { estado: "listo", borrador } });
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setResultado({ clave, valor: { estado: "error", error } });
      },
    );
    return () => {
      vigente = false;
      const propio = abierto.current;
      abierto.current = null;
      if (propio !== null && propio.cambios === 0) descartar(propio.id);
    };
  }, [proyecto, version, clave, alExpirar]);

  // Vuelve a leer el borrador del servidor (por ejemplo al volver a la pestaña del navegador): si ya no está, lo dice.
  const refrescar = useCallback(() => {
    const propio = abierto.current;
    if (propio === null) return;
    pedir<BorradorVivo>(`/v1/hoja/borradores/${propio.id}`).then(
      (vivo) => {
        if (abierto.current?.id !== propio.id) return;
        abierto.current = { id: vivo.id, cambios: vivo.resumen.cambios };
        setResultado((anterior) =>
          anterior !== null && anterior.valor.estado === "listo"
            ? {
                clave: anterior.clave,
                valor: { estado: "listo", borrador: { ...anterior.valor.borrador, base: vivo.base, resumen: vivo.resumen } },
              }
            : anterior,
        );
      },
      (error: unknown) => {
        if (abierto.current?.id !== propio.id) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        abierto.current = null;
        setResultado((anterior) => (anterior === null ? anterior : { clave: anterior.clave, valor: { estado: "error", error } }));
      },
    );
  }, [alExpirar]);

  const reabrir = useCallback(() => setIntento((n) => n + 1), []);

  let estado: EstadoBorrador = { estado: "inactivo" };
  if (clave !== null) estado = resultado?.clave === clave ? resultado.valor : { estado: "abriendo" };
  return { estado, refrescar, reabrir };
}
