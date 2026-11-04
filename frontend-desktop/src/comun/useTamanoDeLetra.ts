import { useSyncExternalStore } from "react";
import { tamanoAplicado } from "./preferenciaDeLetra";
import type { TamanoDeLetra } from "./preferenciaDeLetra";

// Por qué existe: la barra lateral (F4, Tarea 0) pliega «Empresa» según el tamaño de letra y debe reaccionar cuando la
// persona lo cambia sin recargar; `visor/useZoomHoja` ya vigilaba ese mismo atributo, así que la observación se
// comparte aquí (segundo uso, §6.4). El tamaño vive en `data-silice-letra` de <html>, donde lo deja `aplicarTamanoLetra`.
function suscribir(avisar: () => void): () => void {
  const observador = new MutationObserver(avisar);
  observador.observe(document.documentElement, { attributes: true, attributeFilter: ["data-silice-letra"] });
  return () => observador.disconnect();
}

// `useSyncExternalStore` (y no un estado con efecto) porque el atributo es una fuente externa y así no hay un primer
// render con un tamaño y un segundo con otro.
export function useTamanoDeLetra(): TamanoDeLetra {
  return useSyncExternalStore(suscribir, tamanoAplicado);
}
