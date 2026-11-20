// Lógica pura de guardar la versión (rebanada 3d-1: S1 del diseño §4.5 y E9 del §4.4). Los montos llegan como texto
// `{texto, exacto}`; aquí solo se formatean, nunca se convierten a número.
import { ErrorDeApi } from "../../api/cliente";
import { mensajeDeError } from "../../comun/errores";
import { formatoEsVe } from "../../indicadores/formatoEsVe";
import { esBorradorAusente } from "./logica";
import type { Monto, VersionesRespuesta } from "./logica";

export interface CambioDeVersion {
  objeto: string;
  clave: string;
  campo: string;
  antes: string;
  despues: string;
  // Acta DS-75: el insumo de la línea del APU que nombra la clave («{partida}|{rubro}|{n}»); null en otra clave.
  insumo?: string | null;
}

export interface GuardadoRespuesta {
  codigo: string;
  proyecto: string;
  cambios: number;
  total: Monto;
  primera: boolean;
  mensaje: string;
  // Anexo A.6: falso si solo se guardó el desglose del desperdicio (`codigo` es la versión abierta, que sigue igual).
  version_nueva?: boolean;
  desgloses?: number;
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
  // Anexo A.6: lo único que cambió es el desglose del desperdicio (no se pide fuente: la traza no tiene dónde guardarla).
  soloDesglose?: boolean;
}

// Si lo único que cambió en el borrador son desgloses del desperdicio: guardar no crea versión (anexo A.6).
export function esSoloDesglose(primera: boolean, cambios: number, desgloses: number): boolean {
  return !primera && cambios > 0 && desgloses === cambios;
}

const lineas = (n: number) => (n === 1 ? "1 línea" : `${n} líneas`);

export function textoDeDesgloseAGuardar(n: number, version: string): string {
  return `Se guardará el desglose del desperdicio de ${lineas(n)}. La cantidad no cambia, así que la versión ${version} sigue siendo la misma.`;
}

// La mezcla (celdas y desgloses): la versión registra solo las celdas; los desgloses se dicen aparte (arbitraje de A.6, DS-48i).
export function textoDeVersionAGuardar(cambios: number, desgloses: number, version: string): string {
  const celdas = cambios - desgloses;
  const registrados = `Se ${celdas === 1 ? "registrará" : "registrarán"} ${textoDeCambiosAGuardar(celdas)} en una versión nueva (sale de la ${version}).`;
  return desgloses > 0 ? `${registrados} Con ella se guarda también el desglose del desperdicio de ${lineas(desgloses)}.` : registrados;
}

// Por qué una versión de solo lectura no se guarda (la dicen el diálogo de guardar y la nota de solo lectura, F4 2b).
export const CAUSA_SOLO_LECTURA = "alguna partida ya no tiene composición vigente en el catálogo";

// Por qué no se puede guardar todavía, o null si se puede (ui/hoja.py:1786 y 1882; el servidor vuelve a validar).
export function motivoParaNoGuardar({ fuente, primera, cambios, soloLectura, soloDesglose = false }: DatosParaGuardar): string | null {
  if (soloLectura) {
    return `Esta versión está en solo lectura: ${CAUSA_SOLO_LECTURA}.`;
  }
  if (!primera && cambios === 0) return "No hay cambios para guardar: edite alguna celda primero.";
  if (soloDesglose) return null;
  if (fuente.trim() === "") {
    return primera
      ? "Escriba la fuente de la medida: de dónde salen los datos (un plano, un acta)."
      : "Escriba la fuente del cambio: por qué se cambia y con qué respaldo.";
  }
  return null;
}

// Prueba en vivo del 18/11/2026: guardar con partidas «Pendiente» se permite, pero la versión queda con ese error (ERROR del
// informe) y no se puede enviar a aprobación; el diálogo lo dice antes. null si no hay ninguna.
export function textoDePendientesAlGuardar(n: number): string | null {
  if (n <= 0) return null;
  return n === 1
    ? "1 partida está sin precio («Pendiente»): la versión se guardará con ese error y no se podrá enviar a aprobación hasta valorarla. En Partidas, el estado de la fila dice por qué."
    : `${n} partidas están sin precio («Pendiente»): la versión se guardará con ese error y no se podrá enviar a aprobación hasta valorarlas. En Partidas, el estado de cada fila dice por qué.`;
}

export function textoDeCambiosAGuardar(n: number): string {
  return n === 1 ? "1 cambio" : `${n} cambios`;
}

// Lo que se le dice a la persona al guardar (P:497-500 y 539-544, con tildes; el `mensaje` del servidor no se usa).
export function textoDeExito(r: GuardadoRespuesta, proyecto: string): string {
  if (r.version_nueva === false) {
    return `Se guardó el desglose del desperdicio de ${lineas(r.desgloses ?? 0)}. La cantidad no cambió, así que la versión ${r.codigo} sigue siendo la misma.`;
  }
  if (r.primera) {
    return (
      `Se guardó la primera versión ${r.codigo} de la obra ${proyecto} (total ${formatoEsVe(r.total.texto)}). ` +
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
// borrador ya se guardó; «ausente»: el borrador ya no está (o el caso cambió); «desglose-ya-guardado» (422 del anexo A.6: otro ya
// guardó ese desglose y el servidor vació la cuenta del borrador); «permiso», «rechazo» (422), «base» (503), «otro».
export type ClaseDeErrorDeGuardado =
  | "mas-nueva"
  | "rev"
  | "ya-guardado"
  | "ausente"
  | "desglose-ya-guardado"
  | "permiso"
  | "rechazo"
  | "base"
  | "otro";

// El 422 de `aplicacion/hoja_guardado.py` (DESGLOSE_YA_GUARDADO): no se escribió nada, pero el borrador dejó de contar ese desglose.
export const DESGLOSE_YA_GUARDADO = "Ese desglose ya está guardado.";

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
  if (error.estado === 422) {
    return { clase: d === DESGLOSE_YA_GUARDADO ? "desglose-ya-guardado" : "rechazo", mensaje, version: null };
  }
  if (error.estado === 503) return { clase: "base", mensaje: d === "" ? MENSAJE_DE_BASE : mensaje, version: null };
  return { clase: "otro", mensaje, version: null };
}

// La lista de versiones con la `codigo` recién guardada (vigente y por omisión) cuando no se pudo volver a leer del servidor:
// así el selector la tiene y la hoja abre la versión nueva en vez de caer en otra.
export function conVersionGuardada(lista: VersionesRespuesta, codigo: string): VersionesRespuesta {
  const resto = lista.versiones.filter((v) => v.codigo !== codigo).map((v) => ({ ...v, vigente: false }));
  const propia = lista.versiones.find((v) => v.codigo === codigo);
  const nueva = { codigo: "", fecha: "", motivo: "", origen: "", vigente: true, descartada: false, cambios: 0, ...propia };
  return { ...lista, por_omision: codigo, versiones: [{ ...nueva, codigo, vigente: true }, ...resto] };
}
