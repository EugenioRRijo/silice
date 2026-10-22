import { useEffect, useRef } from "react";

// El TextInput y el TextArea de Carbon montan siempre un <span role="alert" aria-live> vacio (el anuncio del contador de
// caracteres), aunque no haya contador: con 4 a 8 campos por pagina el lector de pantalla encuentra otras tantas regiones
// vivas sin contenido (VB-18, VD-6). Este gancho devuelve la ref de la envoltura del campo y, solo al montar, les quita
// los atributos de region viva a las que coinciden con `selector`. Con contador activo no toca nada.
//
// Una sola vez al montar: React no vuelve a escribir atributos que no cambian, y con cientos de campos (900 en el Plan)
// repetirlo en cada render pesaba.
export function useSinRegionVacia<T extends HTMLElement>(selector: string, conContador: boolean) {
  const raiz = useRef<T>(null);
  useEffect(() => {
    if (conContador) return;
    raiz.current?.querySelectorAll(selector).forEach((region) => {
      region.removeAttribute("role");
      region.removeAttribute("aria-live");
      region.removeAttribute("aria-atomic");
    });
  }, [selector, conContador]);
  return raiz;
}
