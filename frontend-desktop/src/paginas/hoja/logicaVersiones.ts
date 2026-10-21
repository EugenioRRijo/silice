// Lógica pura de las operaciones que crean una versión desde una guardada (rebanada 3d-2: S2 a S5 del diseño §4.5) y de la
// lectura de la cadena de sellos (S6). Contrato: `docs/bitacora/2026-10-20-hoja-3d2-contrato-rutas.md`. El precio viaja como el
// texto que se escribió; la interfaz no lo convierte a número.
import { ErrorDeApi } from "../../api/cliente";
import { mensajeDeError } from "../../comun/errores";
import type { CeldaPrecio } from "./logica";
import { MENSAJE_DE_BASE } from "./logicaGuardar";

export const RUTA_DE_RESTAURAR = "/v1/hoja/versiones/restaurar";
export const RUTA_DE_COTIZAR = "/v1/hoja/versiones/cotizar";
export const RUTA_DE_RETIRAR = "/v1/hoja/versiones/retirar-cotizacion";
export const RUTA_DE_CONVERTIR = "/v1/hoja/versiones/convertir";
export const rutaDeCadena = (proyecto: string) => `/v1/hoja/cadena?proyecto=${encodeURIComponent(proyecto)}`;

// Lo que contestan S2 a S5: la versión nueva (que la página abre) y el texto de lo que pasó.
export interface VersionCreada {
  codigo: string;
  proyecto: string;
  mensaje: string;
}

export interface CadenaRespuesta {
  integra: boolean;
  mensaje: string;
  // Las versiones selladas retroactivamente, o null.
  declaracion: string | null;
}

// El responsable nunca viaja: lo pone el servidor desde la sesión (RF-82).
export function cuerpoDeRestaurar(proyecto: string, version: string, fuente: string) {
  return { proyecto, version, fuente };
}

export interface DatosDeCotizacion {
  insumo: string;
  precio: string;
  proveedor: string;
  numero: string;
  fecha: string;
  evidencia: string;
}

export function cuerpoDeCotizar(proyecto: string, version: string, d: DatosDeCotizacion) {
  return {
    proyecto,
    version,
    insumo: d.insumo,
    precio: d.precio,
    proveedor: d.proveedor,
    numero: d.numero,
    fecha: d.fecha,
    evidencia: d.evidencia.trim() === "" ? null : d.evidencia,
  };
}

export function cuerpoDeRetirar(proyecto: string, version: string, insumo: string, motivo: string) {
  return { proyecto, version, insumo, motivo };
}

export type LadoDeLaTasa = "venta" | "compra";

export function cuerpoDeConvertir(proyecto: string, version: string, moneda: string, lado: LadoDeLaTasa, fuente: string) {
  return { proyecto, version, moneda, lado, fuente };
}

export type Operacion = "restaurar" | "cotizar" | "retirar" | "convertir";

// Con cambios sin guardar no se ofrece la operación (ui/paginas/hoja.py:1946, 2081 y 2201; con tildes). Retirar comparte el aviso
// de cotizar, como en la clásica.
export function avisoDeCambiosPendientes(operacion: "restaurar" | "cotizar" | "convertir", cambios: number): string {
  if (operacion === "restaurar") return "Guarde o descarte los cambios pendientes antes de restaurar otra versión.";
  const que = cambios === 1 ? "el cambio pendiente" : `los ${cambios} cambios pendientes`;
  const quien = operacion === "cotizar" ? "Cotizar" : "Cambiar la moneda";
  return `${quien} crea una versión nueva desde la guardada: guarde o descarte primero ${que}.`;
}

export interface CamposDeCotizacion {
  precio: string;
  proveedor: string;
  numero: string;
  fecha: string;
}

const vacio = (texto: string) => texto.trim() === "";

// Qué falta para poder enviar, o null. Solo se mira que no falte nada: si el precio es un decimal válido lo juzga el servidor.
export function motivoParaNoCotizar(c: CamposDeCotizacion): string | null {
  if (vacio(c.precio)) return "Escriba el precio cotizado.";
  if (vacio(c.proveedor)) return "Escriba el proveedor de la cotización.";
  if (vacio(c.numero)) return "Escriba el número de la cotización.";
  if (vacio(c.fecha)) return "Elija la fecha de la cotización.";
  return null;
}

export const motivoParaNoRetirar = (motivo: string): string | null =>
  vacio(motivo) ? "Escriba por qué se retira la cotización." : null;
export const motivoParaNoRestaurar = (fuente: string): string | null =>
  vacio(fuente) ? "Escriba la fuente: por qué se restaura la versión." : null;
export const motivoParaNoConvertir = (fuente: string): string | null =>
  vacio(fuente) ? "Escriba por qué se cambia la moneda (la fuente)." : null;

// El servidor compone el mensaje (con tildes, una sola copia); el de repuesto solo se usa si llegara vacío.
export function textoDeVersionCreada(r: VersionCreada, repuesto: string): string {
  return r.mensaje.trim() === "" ? repuesto : r.mensaje;
}

export type ClaseDeErrorDeOperacion = "rechazo" | "ausente" | "conflicto" | "permiso" | "base" | "otro";

export interface ErrorDeOperacion {
  clase: ClaseDeErrorDeOperacion;
  mensaje: string;
}

// El `detalle` del servidor va tal cual (ni SQL ni rutas: el servidor ya los quita); aquí solo se decide el título y el color.
export function clasificarErrorDeOperacion(error: unknown): ErrorDeOperacion {
  const mensaje = mensajeDeError(error);
  if (!(error instanceof ErrorDeApi)) return { clase: "otro", mensaje };
  if (error.estado === 404) return { clase: "ausente", mensaje };
  if (error.estado === 409) return { clase: "conflicto", mensaje };
  if (error.estado === 403) return { clase: "permiso", mensaje };
  if (error.estado === 422) return { clase: "rechazo", mensaje };
  if (error.estado === 503) return { clase: "base", mensaje: error.detalle === "" ? MENSAJE_DE_BASE : mensaje };
  return { clase: "otro", mensaje };
}

export const TITULO_DE_ERROR: Record<Operacion, string> = {
  restaurar: "No se restauró nada",
  cotizar: "No se guardó nada",
  retirar: "No se guardó nada",
  convertir: "No se convirtió nada",
};

// --- lo que ofrece la tabla de precios (R12) ---

export interface InsumoDePrecios {
  codigo: string;
  insumo: string;
  // El texto de la columna «Cotización»; vacío si el insumo no tiene cotización propia.
  cotizacion: string;
}

function texto(celda: CeldaPrecio | undefined): string {
  return typeof celda === "string" ? celda : "";
}

export function insumosDePrecios(filas: Array<Record<string, CeldaPrecio | undefined>>): InsumoDePrecios[] {
  return filas.flatMap((f) => {
    const codigo = texto(f["codigo"]);
    return codigo === "" ? [] : [{ codigo, insumo: texto(f["insumo"]), cotizacion: texto(f["cotizacion"]) }];
  });
}

export function cotizadasDePrecios(filas: Array<Record<string, CeldaPrecio | undefined>>): InsumoDePrecios[] {
  return insumosDePrecios(filas).filter((i) => i.cotizacion !== "");
}

export const rotuloDeInsumo = (i: InsumoDePrecios) => `${i.codigo} · ${i.insumo}`;
export const rotuloDeCotizada = (i: InsumoDePrecios) => `${i.codigo} · ${i.insumo} (${i.cotizacion})`;

// --- fecha y monedas ---

function dos(n: number): string {
  return String(n).padStart(2, "0");
}

// AAAA-MM-DD con los componentes locales (la fecha por omisión de la cotización: hoy, como `date.today()` de la clásica).
export function fechaDeHoy(ahora: Date = new Date()): string {
  return `${ahora.getFullYear()}-${dos(ahora.getMonth() + 1)}-${dos(ahora.getDate())}`;
}

// MONEDAS de la clásica; la moneda destino no puede ser la actual.
export const MONEDAS = ["Bs", "USD"] as const;

export function monedasDestino(actual: string | null): string[] {
  return MONEDAS.filter((m) => m !== actual);
}
