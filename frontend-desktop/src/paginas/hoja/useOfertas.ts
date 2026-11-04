import { useCallback, useEffect, useState } from "react";
import { ErrorDeApi, pedir } from "../../api/cliente";
import { RUTA_DE_BORRADORES, ofertasDeRetomar } from "./logicaRetomar";
import type { OfertaDeRetomar } from "./logicaRetomar";

type Ofertas = { estado: "buscando" } | { estado: "listo"; lista: OfertaDeRetomar[] };

// Los borradores con cambios que el servidor conserva de este proyecto (E10): se piden al abrir la hoja, antes de abrir uno
// nuevo. Si la lectura falla no se ofrece nada: abrir la hoja no depende de ella. Vivía en `paginas/hoja/index.tsx`; la
// Tarea 3 del plan F4 lo saca a su archivo porque ahora lo usa `ProveedorDeLaHoja`, que ya pasa de 250 líneas.
export function useOfertas(proyecto: string, nombre: string | null, alExpirar: () => void) {
  const [intento, setIntento] = useState(0);
  const [res, setRes] = useState<{ clave: string; lista: OfertaDeRetomar[] } | null>(null);
  const clave = JSON.stringify([proyecto, intento]);
  useEffect(() => {
    let vigente = true;
    pedir<unknown>(RUTA_DE_BORRADORES).then(
      (r) => {
        if (vigente) setRes({ clave, lista: ofertasDeRetomar(r, proyecto, nombre) });
      },
      (error: unknown) => {
        if (!vigente) return;
        if (error instanceof ErrorDeApi && error.estado === 401) alExpirar();
        setRes({ clave, lista: [] });
      },
    );
    return () => {
      vigente = false;
    };
  }, [clave, proyecto, nombre, alExpirar]);
  const recargar = useCallback(() => setIntento((n) => n + 1), []);
  const ofertas: Ofertas = res?.clave === clave ? { estado: "listo", lista: res.lista } : { estado: "buscando" };
  return { ofertas, recargar };
}
