import { useCallback, useEffect, useRef, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { esperarEnvios } from "./envioPendiente";
import type { BorradorAbierto, BorradorVivo, Resumen } from "./logica";

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

// Al irse de la página sin cambios en el borrador: se descarta, pero primero terminan las ediciones que salieron al desmontar
// (la pausa de 400 ms no llegó a cumplirse). Si alguna dejó cambios, el borrador se conserva para retomarlo. Los envíos se anotan
// en el mismo desmontaje, así que basta esperar un turno antes de mirar cuáles hay.
function descartarSiNoQuedanCambios(id: string): void {
  void Promise.resolve()
    .then(() => esperarEnvios(id))
    .then((resumenes) => {
      if (resumenes.some((r) => r !== null && r.cambios > 0)) return;
      descartar(id);
    });
}

// Abre `version` del `proyecto` (null = proyecto sin versiones; undefined = todavía no se sabe) y descarta el
// borrador al cambiar o al desmontar, salvo que tenga cambios sin guardar: esos se conservan para retomarlos. Con
// `retomarId` no abre uno nuevo: retoma ese borrador (el que ya tiene el servidor, con sus cambios).
export function useBorrador(
  proyecto: string | null,
  version: string | null | undefined,
  alExpirar: () => void,
  retomarId: string | null = null,
) {
  const [intento, setIntento] = useState(0);
  // El resultado lleva la clave de lo que se pidió: si ya no es la de ahora, lo visible es «abriendo».
  const [resultado, setResultado] = useState<{ clave: string; valor: EstadoBorrador } | null>(null);
  const abierto = useRef<Abierto | null>(null);
  const clave =
    proyecto === null || version === undefined ? null : JSON.stringify([proyecto, version, intento, retomarId]);

  useEffect(() => {
    if (proyecto === null || version === undefined || clave === null) return;
    let vigente = true;
    const apertura =
      retomarId !== null
        ? pedir<BorradorVivo>(`/v1/hoja/borradores/${retomarId}`).then(
            (vivo): BorradorAbierto => ({ ...vivo, instantanea: { creadas: 0, mensaje: null } }),
          )
        : pedir<BorradorAbierto>("/v1/hoja/borradores", { metodo: "POST", cuerpo: { proyecto, version } });
    apertura.then(
      (borrador) => {
        if (!vigente) {
          // La persona ya se fue a otra versión: nadie lo va a usar (un borrador retomado tiene cambios y se conserva).
          if (retomarId === null) descartar(borrador.id);
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
      if (propio !== null && propio.cambios === 0) descartarSiNoQuedanCambios(propio.id);
    };
  }, [proyecto, version, clave, retomarId, alExpirar]);

  // Vuelve a leer el borrador del servidor (por ejemplo al volver a la pestaña del navegador): si ya no está, lo dice.
  const refrescar = useCallback((): Promise<void> => {
    const propio = abierto.current;
    if (propio === null) return Promise.resolve();
    return pedir<BorradorVivo>(`/v1/hoja/borradores/${propio.id}`).then(
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

  // El servidor aceptó una edición: su resumen (rev, total, cambios...) es ahora el del borrador. Si quedan cambios, el
  // borrador se conserva al irse de la página (se retoma en 3c-3); sin ellos se descarta.
  const aplicar = useCallback((resumen: Resumen) => {
    if (abierto.current !== null) abierto.current = { ...abierto.current, cambios: resumen.cambios };
    setResultado((anterior) =>
      anterior !== null && anterior.valor.estado === "listo"
        ? { clave: anterior.clave, valor: { estado: "listo", borrador: { ...anterior.valor.borrador, resumen } } }
        : anterior,
    );
  }, []);

  // Borra el borrador del servidor. Devuelve si lo logró; si no, deja el error a la vista y el borrador como estaba.
  const borrarActual = useCallback(async (): Promise<boolean> => {
    const propio = abierto.current;
    if (propio === null) return false;
    try {
      await pedir(`/v1/hoja/borradores/${propio.id}`, { metodo: "DELETE" });
    } catch (error) {
      if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
      setResultado((anterior) => (anterior === null ? anterior : { clave: anterior.clave, valor: { estado: "error", error } }));
      return false;
    }
    abierto.current = null; // ya no está: la limpieza al reabrir no lo vuelve a descartar
    return true;
  }, [alExpirar]);

  // «Descartar cambios»: se borra el borrador del servidor y se abre otro desde la versión guardada.
  const descartarCambios = useCallback(async () => {
    if (await borrarActual()) setIntento((n) => n + 1);
  }, [borrarActual]);

  let estado: EstadoBorrador = { estado: "inactivo" };
  if (clave !== null) estado = resultado?.clave === clave ? resultado.valor : { estado: "abriendo" };
  return { estado, refrescar, reabrir, aplicar, descartarCambios, descartarActual: borrarActual };
}
