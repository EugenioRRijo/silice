import { useEffect } from "react";

export const NOMBRE_DEL_PRODUCTO = "Sílice";

// «Página · Sílice»: el título de la pestaña dice dónde está la persona (VB-15). Sin página, solo «Sílice».
export function useTituloDelDocumento(pagina: string | null): void {
  useEffect(() => {
    // «Acerca de Sílice» ya nombra al producto: no se repite.
    const incluyeProducto = pagina?.includes(NOMBRE_DEL_PRODUCTO) ?? false;
    document.title = !pagina ? NOMBRE_DEL_PRODUCTO : incluyeProducto ? pagina : `${pagina} · ${NOMBRE_DEL_PRODUCTO}`;
  }, [pagina]);
}
