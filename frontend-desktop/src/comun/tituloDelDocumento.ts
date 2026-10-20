import { useEffect } from "react";

export const NOMBRE_DEL_PRODUCTO = "Sílice";

// «Página · Sílice»: el título de la pestaña dice dónde está la persona (VB-15). Sin página, solo «Sílice».
export function useTituloDelDocumento(pagina: string | null): void {
  useEffect(() => {
    document.title = pagina ? `${pagina} · ${NOMBRE_DEL_PRODUCTO}` : NOMBRE_DEL_PRODUCTO;
  }, [pagina]);
}
