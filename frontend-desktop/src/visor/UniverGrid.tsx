import { useEffect, useRef } from "react";
import type { LibroVisualRespuesta } from "../api/tipos";
import type { CrearHojaVisor, HojaVisor } from "./hojaVisor";

interface Props {
  libro: LibroVisualRespuesta;
  crearHoja: CrearHojaVisor;
  // Avisa cuando el visor esta listo (y con null cuando se destruye).
  alCambiarVisor: (visor: HojaVisor | null) => void;
  alFallar: (mensaje: string) => void;
  // Razon de acercamiento con la que ya sale dibujado el lienzo (zoom propio por factor de letra). Solo cuenta al
  // crear: los cambios posteriores llegan por `HojaVisor.fijarZoom`, sin recrear el lienzo.
  zoomInicial: number;
}

// Contenedor del lienzo de Univer. Toda la interaccion con Univer ocurre detras de `crearHoja`
// (adaptadorUniver.ts); este componente solo le da un elemento, espera el visor y lo destruye al irse.
export function UniverGrid({ libro, crearHoja, alCambiarVisor, alFallar, zoomInicial }: Props) {
  const contenedor = useRef<HTMLDivElement>(null);
  const zoomAlCrear = useRef(zoomInicial);
  useEffect(() => {
    zoomAlCrear.current = zoomInicial;
  });

  useEffect(() => {
    const elemento = contenedor.current;
    if (!elemento) return;
    let cancelado = false;
    let visor: HojaVisor | null = null;
    crearHoja(elemento, libro, zoomAlCrear.current)
      .then((v) => {
        if (cancelado) {
          v.destruir();
          return;
        }
        visor = v;
        alCambiarVisor(v);
      })
      .catch(() => {
        if (!cancelado) alFallar("No se pudo dibujar la hoja del libro en este navegador.");
      });
    return () => {
      cancelado = true;
      visor?.destruir();
      alCambiarVisor(null);
    };
  }, [libro, crearHoja, alCambiarVisor, alFallar]);

  // Sin tabIndex ni rol: Univer pone sus propios elementos dentro. La hoja es solo lectura.
  return <div className="hoja-lienzo" ref={contenedor} />;
}
