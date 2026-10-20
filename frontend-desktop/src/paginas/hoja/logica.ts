// Lógica pura de «Hoja del proyecto» (marco de la rebanada 3b-1). Los montos llegan como texto
// `{texto, exacto}` y la página solo los formatea: no calcula ni convierte nada a número.
import { ErrorDeApi } from "../../api/cliente";

export const TITULO = "Hoja del proyecto";
export const SIN_VERSIONES = "Este proyecto aún no tiene versiones";

// El orden de la página clásica (ui/paginas/hoja.py, PESTANAS).
export const PESTANAS = [
  "Espacio y metrajes",
  "APU",
  "Presupuesto",
  "Plan y curva",
  "Punto de equilibrio",
  "Precios",
  "Parámetros",
  "Auditoría",
  "Trazabilidad",
] as const;

export interface Monto {
  texto: string;
  exacto: string;
}

export interface VersionFila {
  codigo: string;
  fecha: string;
  motivo: string;
  origen: string;
  vigente: boolean;
  descartada: boolean;
  cambios: number;
}

export interface VersionesRespuesta {
  proyecto: string;
  moneda: string;
  // La versión que se preselecciona (la regla de la clásica, calculada en el servidor).
  por_omision: string | null;
  versiones: VersionFila[];
}

export interface BaseAbierta {
  proyecto: string;
  version: string | null;
  vigente: string | null;
  lista: string | null;
  espacio_de: string | null;
  solo_lectura: boolean;
  moneda: string;
}

export interface Hallazgos {
  severidad: string;
  total: number;
}

export interface Resumen {
  rev: number;
  moneda: string;
  total: Monto;
  cambios: number;
  pendientes_catalogo: number;
  hallazgos: Hallazgos[];
  hay_plan: boolean;
  version_mas_nueva: string | null;
  guardado_como: string | null;
}

export interface BorradorVivo {
  id: string;
  base: BaseAbierta;
  resumen: Resumen;
}

export interface BorradorAbierto extends BorradorVivo {
  instantanea: { creadas: number; mensaje: string | null };
}

export function rutaDeVersiones(proyecto: string): string {
  return `/v1/hoja/versiones?proyecto=${encodeURIComponent(proyecto)}`;
}

// Las no descartadas; si todas lo están, todas (ui/paginas/hoja.py:417).
export function versionesOfrecidas(versiones: VersionFila[]): VersionFila[] {
  const vivas = versiones.filter((v) => !v.descartada);
  return vivas.length > 0 ? vivas : versiones;
}

export function rotuloDeVersion(version: VersionFila): string {
  return version.vigente ? `${version.codigo} (vigente)` : version.codigo;
}

export function textoDeCambios(cambios: number): string {
  if (cambios === 0) return "Sin cambios sin guardar";
  return cambios === 1 ? "1 cambio sin guardar" : `${cambios} cambios sin guardar`;
}

// El 404 de un borrador que el servidor ya no tiene (reinicio, vencimiento, descarte), no el de un proyecto.
export function esBorradorAusente(error: unknown): boolean {
  return error instanceof ErrorDeApi && error.estado === 404 && error.detalle.startsWith("Ese borrador ya no está");
}
