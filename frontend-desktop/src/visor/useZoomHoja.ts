import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { HojaVisor } from "./hojaVisor";
import {
  ZOOM_INICIAL,
  ZOOM_PASO,
  ajustarZoom,
  factorDeLetra,
  guardarZoomHoja,
  leerZoomHoja,
  pasoDeRueda,
  razonEfectiva,
} from "./zoomHoja";

// Zoom de la hoja: el propio (50 a 300 %) por el factor del tamaño de letra de la interfaz. Aquí vive el estado; el
// lienzo lo recibe como una razón ya multiplicada (`HojaVisor.fijarZoom`), sin recargarse, así que ni la selección ni
// el desplazamiento se pierden. El factor se vigila en el atributo que deja `aplicarTamanoLetra` en la raíz.
export function useZoomHoja(visor: HojaVisor | null) {
  const [zoom, setZoom] = useState<number>(leerZoomHoja);
  const [factor, setFactor] = useState<number>(factorDeLetra);

  useEffect(() => {
    const raiz = document.documentElement;
    const observador = new MutationObserver(() => setFactor(factorDeLetra()));
    observador.observe(raiz, { attributes: true, attributeFilter: ["data-silice-letra"] });
    return () => observador.disconnect();
  }, []);

  const razon = razonEfectiva(zoom, factor);
  const limitado = Math.round((zoom / 100) * factor * 1000) / 1000 > razon;

  useEffect(() => {
    visor?.fijarZoom(razon);
  }, [visor, razon]);

  // El zoom vigente en una ref, para que subir y bajar no dependan de un cierre viejo ni guarden dentro de un updater.
  const vigente = useRef(zoom);
  const fijar = useCallback((nuevo: number) => {
    const ajustado = ajustarZoom(nuevo);
    vigente.current = ajustado;
    setZoom(ajustado);
    guardarZoomHoja(ajustado);
  }, []);
  const subir = useCallback(() => fijar(vigente.current + ZOOM_PASO), [fijar]);
  const bajar = useCallback(() => fijar(vigente.current - ZOOM_PASO), [fijar]);
  const restablecer = useCallback(() => fijar(ZOOM_INICIAL), [fijar]);

  return useMemo(
    () => ({ zoom, factor, razon, limitado, subir, bajar, restablecer }),
    [zoom, factor, razon, limitado, subir, bajar, restablecer],
  );
}

interface Acciones {
  subir: () => void;
  bajar: () => void;
  restablecer: () => void;
}

// Atajos: Ctrl + rueda sobre el lienzo y Ctrl + «+», «-», «0» con el foco dentro de la sección de la hoja. Fuera de
// ella no se intercepta nada, así el zoom del navegador queda intacto. La rueda con Ctrl se atiende en la fase de
// captura para que el zoom propio de Univer (que fijaría otra razón) no la reciba.
// Reciben los elementos (no refs): la hoja se monta cuando el libro termina de cargar, despues del primer render.
export function useAtajosZoom(seccion: HTMLElement | null, lienzo: HTMLElement | null, acciones: Acciones) {
  const ultimas = useRef(acciones);
  useEffect(() => {
    ultimas.current = acciones;
  });

  useEffect(() => {
    const elementoSeccion = seccion;
    if (!elementoSeccion) return;
    const alTeclear = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey) || e.altKey) return;
      if (e.key === "+" || e.key === "=") ultimas.current.subir();
      else if (e.key === "-" || e.key === "_") ultimas.current.bajar();
      else if (e.key === "0") ultimas.current.restablecer();
      else return;
      e.preventDefault();
      e.stopPropagation();
    };
    elementoSeccion.addEventListener("keydown", alTeclear);
    return () => elementoSeccion.removeEventListener("keydown", alTeclear);
  }, [seccion]);

  useEffect(() => {
    const elementoLienzo = lienzo;
    if (!elementoLienzo) return;
    let acumulado = 0;
    const alRodar = (e: WheelEvent) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      e.preventDefault();
      e.stopPropagation();
      const { paso, resto } = pasoDeRueda(acumulado, e.deltaY);
      acumulado = resto;
      if (paso > 0) ultimas.current.subir();
      else if (paso < 0) ultimas.current.bajar();
    };
    elementoLienzo.addEventListener("wheel", alRodar, { capture: true, passive: false });
    return () => elementoLienzo.removeEventListener("wheel", alRodar, { capture: true });
  }, [lienzo]);
}
