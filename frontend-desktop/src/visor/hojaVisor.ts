// Interfaz propia y pequena entre la interfaz de Sílice y el visor de hojas. Univer vive detras de ella
// (adaptadorUniver.ts); en las pruebas de jsdom, donde Univer no dibuja, se usa un doble.
import type { LibroVisualRespuesta } from "../api/tipos";

export interface CeldaRef {
  hoja: string;
  fila0: number;
  columna0: number;
}

// Pixeles CSS relativos a la esquina superior izquierda del lienzo del visor.
export interface RectanguloPx {
  x: number;
  y: number;
  ancho: number;
  alto: number;
}

export interface HojaVisor {
  // Nombre de la hoja que se esta viendo.
  hojaActiva(): string;
  // Cambia de hoja (sin tocar la seleccion).
  irAHoja(nombre: string): void;
  // Cambia de hoja si hace falta, desplaza hasta que la celda se vea y la selecciona.
  irA(celda: CeldaRef): void;
  // Donde esta la celda en el lienzo ahora mismo; null si no esta a la vista (otra hoja, fuera del
  // desplazamiento, fila o columna oculta).
  rectanguloDe(celda: CeldaRef): RectanguloPx | null;
  // La zona de celdas del lienzo (sin las cabeceras A, B, C ni 1, 2, 3): lo que los halos no deben pasar.
  area(): RectanguloPx | null;
  // Se llama cuando cambia lo que se ve: desplazamiento, acercamiento, cambio de hoja o de tamano.
  alCambiar(devolucion: () => void): () => void;
  // Se llama cuando el usuario selecciona una celda en el lienzo.
  alSeleccionar(devolucion: (celda: CeldaRef) => void): () => void;
  destruir(): void;
}

export type CrearHojaVisor = (contenedor: HTMLElement, libro: LibroVisualRespuesta) => Promise<HojaVisor>;
