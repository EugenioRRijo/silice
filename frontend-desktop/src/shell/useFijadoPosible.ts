import { useSyncExternalStore } from "react";

// El umbral desde el que el sidebar puede quedarse fijado vive solo en `_umbrales.scss` (mixin `fijado-posible`): pone
// `--silice-fijado-posible: 1` en <html> desde 1366 px con letra Normal (1708 px Grande, 2049 px Muy grande). Aqui solo
// se lee; por debajo, el fijado se comporta como oculto (diseno de modulos §12.8).
const VARIABLE = "--silice-fijado-posible";

export function leerFijadoPosible(): boolean {
  return getComputedStyle(document.documentElement).getPropertyValue(VARIABLE).trim() === "1";
}

// Cambia al redimensionar la ventana y al cambiar el tamano de letra (`TamanoLetra` pone <html data-silice-letra> y la
// escala en el estilo de <html>).
function suscribir(aviso: () => void): () => void {
  window.addEventListener("resize", aviso);
  const observador = new MutationObserver(aviso);
  observador.observe(document.documentElement, { attributes: true, attributeFilter: ["data-silice-letra", "style"] });
  return () => {
    window.removeEventListener("resize", aviso);
    observador.disconnect();
  };
}

export function useFijadoPosible(): boolean {
  return useSyncExternalStore(suscribir, leerFijadoPosible, () => false);
}
