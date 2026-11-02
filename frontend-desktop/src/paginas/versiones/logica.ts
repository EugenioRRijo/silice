// Lógica pura de la sección Versiones (Tarea 6 del plan F4). Por qué existe: la tabla junta tres lecturas (las versiones
// del proveedor de la Hoja, el estado de aprobación de cada una y cuál está abierta) y la franja decide un solo paso; aquí
// se combinan sin pintar nada, para probarlas sin montar la pantalla. La interfaz no calcula: solo junta lo que da la API.
import type { EstadoDeAprobacion } from "../../comun/aprobacion";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { versionesOfrecidas } from "../hoja/logica";
import type { VersionFila, VersionesRespuesta } from "../hoja/logica";
import { TEXTOS_DEL_PASO } from "../hoja/textos";

export interface FilaDeVersion extends VersionFila {
  // La clave del estado de aprobación (`guardada`, `en_aprobacion`, `devuelta`…), o null si no se pudo leer.
  estado: string | null;
  abierta: boolean;
}

// Las versiones que se pueden abrir (las no descartadas; si todas lo están, todas: la misma regla que el proveedor usa para
// abrir una, así que «Abrir» nunca pide una que abriría otra), cada una con su estado y la marca de la abierta.
export function filasDeVersiones(
  v: VersionesRespuesta,
  estados: Record<string, EstadoDeAprobacion> | null,
  abierta: string | null,
): FilaDeVersion[] {
  return versionesOfrecidas(v.versiones).map((f) => ({
    ...f,
    estado: estados?.[f.codigo]?.estado ?? null,
    abierta: abierta !== null && f.codigo === abierta,
  }));
}

export interface PasoDeVersiones {
  texto: string;
  // «guardar» abre «Guardar versión»; null, la franja solo informa.
  accion: "guardar" | null;
}

// La franja de Versiones: con cambios sin guardar, guardarlos (el botón, solo si se puede guardar); si no, con la vigente en
// aprobación, que espera dictamen. Los textos son los de la franja del Presupuesto (`TEXTOS_DEL_PASO`).
export function pasoDeVersiones(e: { cambios: number; puedeGuardar: boolean; filas: FilaDeVersion[] }): PasoDeVersiones | null {
  if (e.cambios > 0) {
    return { texto: TEXTOS_DEL_PASO.sinGuardar(formatoEsVe(String(e.cambios)), e.cambios === 1), accion: e.puedeGuardar ? "guardar" : null };
  }
  const vigente = e.filas.find((f) => f.vigente);
  if (vigente?.estado === "en_aprobacion") return { texto: TEXTOS_DEL_PASO.enAprobacion(vigente.codigo), accion: null };
  return null;
}
