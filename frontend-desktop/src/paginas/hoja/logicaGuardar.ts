// Lógica pura de guardar la versión (rebanada 3d-1: S1 del diseño §4.5 y E9 del §4.4). Los montos llegan como texto
// `{texto, exacto}`; aquí solo se formatean, nunca se convierten a número.
import { ErrorDeApi } from "../../api/cliente";
import { mensajeDeError } from "../../comun/errores";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { esBorradorAusente } from "./logica";
import type { Monto } from "./logica";

export interface CambioDeVersion {
  objeto: string;
  clave: string;
  campo: string;
  antes: string;
  despues: string;
}

export interface GuardadoRespuesta {
  codigo: string;
  proyecto: string;
  cambios: number;
  total: Monto;
  primera: boolean;
  mensaje: string;
}

export const rutaDeGuardar = (id: string) => `/v1/hoja/borradores/${id}/guardar`;
export const rutaDeCambios = (id: string) => `/v1/hoja/borradores/${id}/cambios`;

// El responsable nunca viaja: lo pone el servidor desde la sesión (RF-82).
export function cuerpoDeGuardado(rev: number, fuente: string, confirmarVersionMasNueva: boolean): object {
  return confirmarVersionMasNueva ? { rev, fuente, confirmar_version_mas_nueva: true } : { rev, fuente };
}

function esCambio(x: unknown): x is CambioDeVersion {
  if (x === null || typeof x !== "object") return false;
  const c = x as Record<string, unknown>;
  return ["objeto", "clave", "campo", "antes", "despues"].every((k) => typeof c[k] === "string");
}

// La lista de cambios que contesta E9 (sola o envuelta en `cambios`); null si no es una lista.
export function cambiosDeRespuesta(respuesta: unknown): CambioDeVersion[] | null {
  const lista =
    Array.isArray(respuesta)
      ? respuesta
      : respuesta !== null && typeof respuesta === "object"
        ? (respuesta as Record<string, unknown>)["cambios"]
        : null;
  return Array.isArray(lista) ? lista.filter(esCambio) : null;
}

export const FUENTE_DEL_CAMBIO = "Fuente del cambio (por qué y con qué respaldo)";
export const FUENTE_DE_LA_MEDIDA = "Fuente de la medida (de dónde salen los datos)";

export interface DatosParaGuardar {
  fuente: string;
  primera: boolean;
  cambios: number;
  soloLectura: boolean;
}

// Por qué no se puede guardar todavía, o null si se puede (ui/hoja.py:1786 y 1882; el servidor vuelve a validar).
export function motivoParaNoGuardar({ fuente, primera, cambios, soloLectura }: DatosParaGuardar): string | null {
  if (soloLectura) {
    return "Esta versión está en solo lectura: alguna partida ya no tiene composición vigente en el catálogo.";
  }
  if (!primera && cambios === 0) return "No hay cambios para guardar: edite alguna celda primero.";
  if (fuente.trim() === "") {
    return primera
      ? "Escriba la fuente de la medida: de dónde salen los datos (un plano, un acta)."
      : "Escriba la fuente del cambio: por qué se cambia y con qué respaldo.";
  }
  return null;
}

export function textoDeCambiosAGuardar(n: number): string {
  return n === 1 ? "1 cambio" : `${n} cambios`;
}

// Lo que se le dice a la persona al guardar (P:497-500 y 539-544, con tildes; el `mensaje` del servidor no se usa).
export function textoDeExito(r: GuardadoRespuesta, proyecto: string): string {
  if (r.primera) {
    return (
      `Se guardó la primera versión ${r.codigo} del proyecto ${proyecto} (total ${formatoEsVe(r.total.texto)}). ` +
      "Quedó registrada su creación, con su fuente y su responsable."
    );
  }
  const registrados = r.cambios === 1 ? "1 cambio registrado" : `${r.cambios} cambios registrados`;
  return `Se guardó la versión ${r.codigo} con ${registrados}.`;
}

export function usuarioDeSesion(sesion: { nombre: string; login: string }): string {
  return `${sesion.nombre} <${sesion.login}>`;
}

// «mas-nueva»: otra persona guardó una versión después; «rev»: el borrador cambió en otra ventana; «ya-guardado»: este
// borrador ya se guardó; «ausente»: el borrador ya no está (o el caso cambió); «permiso», «rechazo» (422), «base» (503), «otro».
export type ClaseDeErrorDeGuardado = "mas-nueva" | "rev" | "ya-guardado" | "ausente" | "permiso" | "rechazo" | "base" | "otro";

export interface ErrorDeGuardado {
  clase: ClaseDeErrorDeGuardado;
  mensaje: string;
  // La versión de que habla el mensaje («004» en «Otra persona guardó la versión 004…» o «ya se guardó como la versión 004»).
  version: string | null;
}

export const MENSAJE_DE_BASE =
  "No se pudo leer o escribir el caso. Revise que el archivo exista y no esté abierto en otro programa.";

// La versión nueva que trae el 409 como segundo campo del cuerpo (contrato 3d-1), o null.
function versionDelCuerpo(cuerpo: unknown): string | null {
  if (cuerpo === null || typeof cuerpo !== "object") return null;
  const v = (cuerpo as Record<string, unknown>)["version_mas_nueva"];
  return typeof v === "string" && v !== "" ? v : null;
}

function versionDe(detalle: string, patron: RegExp): string | null {
  return patron.exec(detalle)?.[1] ?? null;
}

export function clasificarErrorDeGuardado(error: unknown): ErrorDeGuardado {
  const mensaje = mensajeDeError(error);
  if (!(error instanceof ErrorDeApi)) return { clase: "otro", mensaje, version: null };
  const d = error.detalle;
  if (error.estado === 404 && esBorradorAusente(error)) return { clase: "ausente", mensaje, version: null };
  if (error.estado === 409) {
    if (d.startsWith("Otra persona guardó")) {
      return { clase: "mas-nueva", mensaje, version: versionDelCuerpo(error.cuerpo) ?? versionDe(d, /guardó la versión ([^\s.,;]+)/) };
    }
    if (d.startsWith("El borrador cambió")) return { clase: "rev", mensaje, version: null };
    if (d.startsWith("Este borrador ya se guardó")) {
      return { clase: "ya-guardado", mensaje, version: versionDe(d, /como la versión ([^\s.,;]+)/) };
    }
    if (d.startsWith("El caso cambió")) return { clase: "ausente", mensaje, version: null };
    return { clase: "otro", mensaje, version: null };
  }
  if (error.estado === 403) return { clase: "permiso", mensaje, version: null };
  if (error.estado === 422) return { clase: "rechazo", mensaje, version: null };
  if (error.estado === 503) return { clase: "base", mensaje: d === "" ? MENSAJE_DE_BASE : mensaje, version: null };
  return { clase: "otro", mensaje, version: null };
}
