// Doble de HojaVisor para las pruebas: Univer no dibuja en jsdom. No lo importa codigo de produccion.
import { vi } from "vitest";
import type { CeldaRef, HojaVisor, RectanguloPx } from "./hojaVisor";

export interface HojaFalsa extends HojaVisor {
  // Dispara los avisos como lo haria Univer al desplazar o al hacer clic en una celda.
  cambiar(): void;
  seleccionar(celda: CeldaRef): void;
  fijarHoja(nombre: string): void;
  posiciones: Map<string, RectanguloPx | null>;
  irA: ReturnType<typeof vi.fn<(celda: CeldaRef) => void>>;
  irAHoja: ReturnType<typeof vi.fn<(nombre: string) => void>>;
  destruir: ReturnType<typeof vi.fn<() => void>>;
  fijarZoom: ReturnType<typeof vi.fn<(razon: number) => void>>;
}

export function clave(c: CeldaRef): string {
  return `${c.hoja}!${c.fila0},${c.columna0}`;
}

export function crearHojaFalsa(hojaInicial = "PRESUPUESTO"): HojaFalsa {
  let hojaActual = hojaInicial;
  const posiciones = new Map<string, RectanguloPx | null>();
  const avisosCambio = new Set<() => void>();
  const avisosSeleccion = new Set<(c: CeldaRef) => void>();
  let razonActual = 1;
  return {
    posiciones,
    hojaActiva: () => hojaActual,
    irAHoja: vi.fn((nombre: string) => {
      hojaActual = nombre;
      avisosCambio.forEach((f) => f());
    }),
    irA: vi.fn((celda: CeldaRef) => {
      hojaActual = celda.hoja;
      avisosCambio.forEach((f) => f());
    }),
    rectanguloDe: (celda) => (celda.hoja === hojaActual ? (posiciones.get(clave(celda)) ?? null) : null),
    area: () => ({ x: 46, y: 20, ancho: 700, alto: 400 }),
    alCambiar: (f) => {
      avisosCambio.add(f);
      return () => avisosCambio.delete(f);
    },
    alSeleccionar: (f) => {
      avisosSeleccion.add(f);
      return () => avisosSeleccion.delete(f);
    },
    fijarZoom: vi.fn((razon: number) => {
      razonActual = razon;
      avisosCambio.forEach((f) => f());
    }),
    zoomActual: () => razonActual,
    destruir: vi.fn(),
    cambiar: () => avisosCambio.forEach((f) => f()),
    seleccionar: (c) => avisosSeleccion.forEach((f) => f(c)),
    fijarHoja: (nombre) => {
      hojaActual = nombre;
    },
  };
}
