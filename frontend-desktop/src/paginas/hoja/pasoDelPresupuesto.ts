// Esbozo del rojo (Tarea 5 del plan F4): solo los tipos, para que las pruebas fallen por lo que dicen y no por una
// importación ausente. La implementación llega con el commit `feat`.
import type { Hallazgos } from "./logica";

export type AccionDelPresupuesto = "agregar_partida" | "guardar" | "ver_revision" | "version_nueva" | "enviar_a_aprobacion";

export interface EntradaDelPaso {
  version: string | null;
  vigente: string | null;
  cambios: number;
  graves: number;
  aprobacion: string | null;
  puedeEditar: boolean;
  puedeEnviar: boolean;
}

export interface PasoDelPresupuesto {
  tipo: "falta" | "siguiente";
  texto: string;
  accion: AccionDelPresupuesto | null;
}

export function pasoDelPresupuesto(e: EntradaDelPaso): PasoDelPresupuesto | null {
  void e;
  return null;
}

export function gravesDe(hallazgos: readonly Hallazgos[]): number {
  void hallazgos;
  return 0;
}

export function esFilaAfectada(severidad: string | null): boolean {
  void severidad;
  return false;
}

export function necesitaLaAprobacion(e: Pick<EntradaDelPaso, "version" | "cambios" | "graves">): boolean {
  void e;
  return false;
}
