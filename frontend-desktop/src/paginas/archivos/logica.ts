// ESBOZO DEL ROJO (Tarea 11 de F4): las firmas de la lógica de Archivos y planos, sin implementar.
import type { FilaDensa } from "../../comun/TablaDensa";

export interface ImportacionDeObra {
  tipo: "plano" | "computo";
  archivo: string;
  fecha_hora: string;
  usuario: string;
  resumen: string;
  version: string | null;
  guardada: boolean;
}

export interface ImportacionesRespuesta {
  importaciones: ImportacionDeObra[];
}

export type FlujoDeArchivo = "plano" | "computo";

export function rutaDeImportaciones(proyecto: string): string {
  return proyecto;
}

export function tipoDeImportacion(tipo: ImportacionDeObra["tipo"], archivo: string): string {
  return `${tipo}${archivo}`.slice(0, 0);
}

export function filasDeImportaciones(r: ImportacionesRespuesta): FilaDensa[] {
  return r.importaciones.slice(0, 0).map((_, i) => ({ id: String(i) }));
}

export function flujoDelArchivo(nombre: string): FlujoDeArchivo | null {
  return nombre === "" ? null : null;
}

export function extensionesDeSubida(conComputo: boolean): string[] {
  return conComputo ? [] : [];
}

export function etiquetaDeSubida(conComputo: boolean): string {
  return conComputo ? "" : "";
}
